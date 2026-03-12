"""
Paper Trading Engine for Tiger Open API.

Handles:
- Order placement (market, limit, stop)
- Order tracking and cancellation
- Position management
- P&L calculation (simulated for paper trading)
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid

from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.trade.trade_client import TradeClient
from tigeropen.trade.model import Order, Contract

from config import (
    TIGER_ID, ACCOUNT_ID, PRIVATE_KEY_PATH, SANDBOX_MODE,
    MAX_POSITION_SIZE, DAILY_LOSS_LIMIT, MAX_ORDER_RETRIES
)

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Position:
    """Represents an open position."""
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    side: OrderSide = OrderSide.BUY

    def update_price(self, price: float):
        """Update position with latest price and recalculate P&L."""
        self.current_price = price
        if self.side == OrderSide.BUY:
            self.unrealized_pnl = (price - self.avg_cost) * self.quantity
        else:
            self.unrealized_pnl = (self.avg_cost - price) * self.quantity


@dataclass
class OrderRecord:
    """Track an order from placement to completion."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: int = 0
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    tiger_order_id: Optional[str] = None  # Tiger's order ID

    @property
    def is_active(self) -> bool:
        return self.status in (OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED)


class PaperTrader:
    """
    Paper trading engine that executes orders via Tiger Open API
    in sandbox mode with local P&L tracking.
    """

    def __init__(self, tiger_id: str = TIGER_ID, account_id: str = ACCOUNT_ID,
                 private_key_path: str = PRIVATE_KEY_PATH,
                 sandbox: bool = SANDBOX_MODE,
                 max_position_size: float = MAX_POSITION_SIZE,
                 daily_loss_limit: float = DAILY_LOSS_LIMIT):
        """Initialize paper trader."""
        self.tiger_id = tiger_id
        self.account_id = account_id
        self.private_key_path = private_key_path
        self.sandbox = sandbox
        self.max_position_size = max_position_size
        self.daily_loss_limit = daily_loss_limit

        self._trade_client: Optional[TradeClient] = None
        self._connected = False

        # Local state tracking (used for quick access & validation)
        self._positions: Dict[str, Position] = {}
        self._orders: Dict[str, OrderRecord] = {}
        self._daily_pnl: float = 0.0
        self._initial_balance: Optional[float] = None

    def connect(self) -> bool:
        """Connect to Tiger Open API."""
        try:
            client_config = TigerOpenClientConfig(sandbox_debug=self.sandbox)
            client_config.private_key = read_private_key(self.private_key_path)
            client_config.tiger_id = self.tiger_id
            client_config.account = self.account_id

            self._trade_client = TradeClient(client_config)

            # Fetch initial account info
            account_info = self._trade_client.get_account_info(self.account_id)
            self._initial_balance = account_info.get('net_liquidation', 0.0)

            self._connected = True
            logger.info("✅ Paper trader connected to Tiger API")
            logger.info(f"   Account: {self.account_id}")
            logger.info(f"   Initial balance: ${self._initial_balance:,.2f}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect paper trader: {e}")
            return False

    def disconnect(self):
        """Disconnect from API."""
        self._connected = False
        logger.info("Paper trader disconnected")

    def is_connected(self) -> bool:
        return self._connected

    def get_account_summary(self) -> Dict[str, Any]:
        """Get full account summary including balance and positions."""
        if not self._trade_client:
            raise RuntimeError("Not connected")

        try:
            info = self._trade_client.get_account_info(self.account_id)
            positions = self._trade_client.get_positions(self.account_id)

            # Merge with local position tracking
            summary = {
                'account_id': self.account_id,
                'net_liquidation': info.get('net_liquidation', 0.0),
                'cash_balance': info.get('cash_balance', 0.0),
                'buying_power': info.get('buying_power', 0.0),
                'daily_pnl': self._daily_pnl,
                'total_pnl': info.get('total_profit_loss', 0.0),
                'positions': positions
            }
            return summary
        except Exception as e:
            logger.error(f"Error fetching account summary: {e}")
            raise

    def get_positions(self) -> Dict[str, Position]:
        """Get current positions (cached from API)."""
        if not self._trade_client:
            raise RuntimeError("Not connected")

        try:
            tiger_positions = self._trade_client.get_positions(self.account_id)
            # Convert to Position objects
            # Adjust based on actual Tiger response format
            self._positions.clear()
            for pos_data in tiger_positions:
                symbol = pos_data.get('symbol', '')
                if symbol:
                    self._positions[symbol] = Position(
                        symbol=symbol,
                        quantity=pos_data.get('quantity', 0),
                        avg_cost=pos_data.get('average_cost', 0.0),
                        current_price=pos_data.get('last_price', 0.0),
                        side=OrderSide(pos_data.get('side', 'BUY'))
                    )
                    self._positions[symbol].update_price(
                        pos_data.get('last_price', 0.0)
                    )
            return self._positions
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            raise

    def place_order(self, symbol: str, side: OrderSide, quantity: int,
                    order_type: OrderType = OrderType.MARKET,
                    limit_price: Optional[float] = None,
                    stop_price: Optional[float] = None) -> OrderRecord:
        """
        Place a new order.

        Args:
            symbol: Ticker symbol
            side: BUY or SELL
            quantity: Number of shares/contracts
            order_type: MARKET, LIMIT, STOP, STOP_LIMIT
            limit_price: Required for LIMIT and STOP_LIMIT orders
            stop_price: Required for STOP and STOP_LIMIT orders

        Returns:
            OrderRecord with order details
        """
        if not self._connected:
            raise RuntimeError("Trader not connected")

        # Pre-trade checks
        if not self._validate_order(symbol, side, quantity, order_type, limit_price, stop_price):
            raise ValueError("Order failed validation")

        # Create order record
        order = OrderRecord(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price
        )

        try:
            # Build Tiger contract
            contract = Contract()
            contract.symbol = symbol
            contract.sec_type = "STK"  # Assuming stock; extend for options/futures
            contract.exchange = "US" if SANDBOX_MODE else "US"  # Adjust as needed

            # Build Tiger order
            tiger_order = Order()
            tiger_order.account = self.account_id
            tiger_order.contract = contract
            tiger_order.order_type = order_type.value
            tiger_order.quantity = quantity

            if limit_price is not None:
                tiger_order.limit_price = limit_price
            if stop_price is not None:
                tiger_order.stop_price = stop_price

            if side == OrderSide.BUY:
                tiger_order.action = "BUY"
            else:
                tiger_order.action = "SELL"

            # Place order via Tiger API
            tiger_order_id = self._trade_client.place_order(tiger_order)
            order.tiger_order_id = tiger_order_id
            order.status = OrderStatus.PENDING

            # Track locally
            self._orders[order.id] = order
            logger.info(f"📤 Order placed: {side.value} {quantity} {symbol} "
                       f"({order_type.value}) - ID: {tiger_order_id}")
            return order

        except Exception as e:
            logger.error(f"❌ Order placement failed: {e}")
            order.status = OrderStatus.REJECTED
            self._orders[order.id] = order
            raise

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        if order_id not in self._orders:
            logger.warning(f"Order {order_id} not found")
            return False

        order = self._orders[order_id]
        if not order.is_active:
            logger.warning(f"Order {order_id} is not active (status: {order.status})")
            return False

        try:
            self._trade_client.cancel_order(order.tiger_order_id)
            order.status = OrderStatus.CANCELLED
            logger.info(f"🗑️ Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Cancel failed for {order_id}: {e}")
            return False

    def update_order(self, tiger_order_id: str, status: str, filled_qty: int, avg_price: float):
        """
        Update order status (called from WebSocket or polling).

        Args:
            tiger_order_id: Tiger's order ID
            status: New status (from Tiger)
            filled_qty: Quantity filled
            avg_price: Average fill price
        """
        # Find matching order
        order = next((o for o in self._orders.values() if o.tiger_order_id == tiger_order_id), None)
        if not order:
            logger.warning(f"Order {tiger_order_id} not tracked locally")
            return

        old_status = order.status
        order.status = OrderStatus(status)
        order.filled_quantity = filled_qty
        order.avg_fill_price = avg_price

        if filled_qty > 0 and order.filled_at is None:
            order.filled_at = datetime.now()

        # Update P&L on fills
        if old_status != OrderStatus.FILLED and order.status == OrderStatus.FILLED:
            self._on_order_filled(order)

        logger.debug(f"Order {tiger_order_id} updated: {status}")

    def _on_order_filled(self, order: OrderRecord):
        """Handle order fill event."""
        logger.info(f"✅ Order filled: {order.symbol} {order.quantity} @ ${order.avg_fill_price:.2f}")

        # Update position
        symbol = order.symbol
        if symbol not in self._positions:
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=0,
                avg_cost=0.0,
                side=order.side
            )

        pos = self._positions[symbol]

        if order.side == OrderSide.BUY:
            # Add to long position
            total_quantity = pos.quantity + order.quantity
            total_cost = (pos.avg_cost * pos.quantity) + (order.avg_fill_price * order.quantity)
            pos.quantity = total_quantity
            pos.avg_cost = total_cost / total_quantity if total_quantity > 0 else 0
            pos.side = OrderSide.BUY
        else:
            # Reduce/sell position
            pos.quantity -= order.quantity
            if pos.quantity <= 0:
                # Position closed - calculate realized P&L
                realized_pnl = (order.avg_fill_price - pos.avg_cost) * order.quantity
                self._daily_pnl += realized_pnl
                logger.info(f"💰 Position closed: {symbol} P&L: ${realized_pnl:.2f}")
                if pos.quantity == 0:
                    self._positions.pop(symbol, None)
                    return

            # Update avg_cost remains same for partial sell

        # Update P&L tracking
        current_value = pos.quantity * order.avg_fill_price
        # Simplified: in real scenario, get current market price
        # For now, use fill price as approximation
        pos.current_price = order.avg_fill_price
        pos.update_price(order.avg_fill_price)

    def _validate_order(self, symbol: str, side: OrderSide, quantity: int,
                        order_type: OrderType, limit_price: Optional[float],
                        stop_price: Optional[float]) -> bool:
        """Validate order parameters before submission."""
        if quantity <= 0:
            logger.error("Quantity must be positive")
            return False

        if order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and limit_price is None:
            logger.error(f"{order_type.value} order requires limit_price")
            return False

        if order_type in (OrderType.STOP, OrderType.STOP_LIMIT) and stop_price is None:
            logger.error(f"{order_type.value} order requires stop_price")
            return False

        # Position size check
        if side == OrderSide.BUY:
            # Estimate cost (use market price if available, else placeholder)
            estimated_cost = limit_price if limit_price else 100.0  # placeholder
            if estimated_cost * quantity > self.max_position_size:
                logger.error(f"Order size exceeds max position limit: ${estimated_cost * quantity:,.2f} > ${self.max_position_size:,.2f}")
                return False

        # Daily loss limit check
        if self._daily_pnl < -self.daily_loss_limit:
            logger.error(f"Daily loss limit reached: ${self._daily_pnl:.2f}")
            return False

        return True

    def get_active_orders(self) -> List[OrderRecord]:
        """Get all active (non-filled, non-cancelled) orders."""
        return [o for o in self._orders.values() if o.is_active]

    def get_order_history(self) -> List[OrderRecord]:
        """Get all orders (active and filled)."""
        return list(self._orders.values())

    def get_open_positions(self) -> Dict[str, Position]:
        """Get current open positions."""
        return self._positions.copy()

    def get_daily_pnl(self) -> float:
        """Get today's realized P&L."""
        return self._daily_pnl