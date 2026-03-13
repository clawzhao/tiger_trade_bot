"""
Paper Trading Engine for Tiger Open API.

Handles:
- Order placement (market, limit, stop)
- Order tracking and cancellation
- Position management
- P&L calculation (simulated for paper trading)
- Retry and exponential backoff on API calls
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid
from functools import lru_cache

from tenacity import retry, stop_after_attempt, wait_exponential

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
    """Enumeration for order sides."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Enumeration for order types."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(Enum):
    """Enumeration for order status."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Position:
    """Represents an open position.

    Attributes:
        symbol (str): Ticker symbol.
        quantity (int): Number of shares/contracts.
        avg_cost (float): Average cost basis.
        current_price (float): Latest known price.
        unrealized_pnl (float): Unrealized profit and loss.
        side (OrderSide): BUY or SELL.
    """
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    side: OrderSide = OrderSide.BUY

    def update_price(self, price: float) -> None:
        """Update position with latest price and recalculate P&L.

        Args:
            price (float): The current market price.
        """
        self.current_price = price
        if self.side == OrderSide.BUY:
            self.unrealized_pnl = (price - self.avg_cost) * self.quantity
        else:
            self.unrealized_pnl = (self.avg_cost - price) * self.quantity


@dataclass
class OrderRecord:
    """Track an order from placement to completion.

    Attributes:
        id (str): Internal unique identifier.
        symbol (str): Ticker symbol.
        side (OrderSide): Buy or sell side.
        order_type (OrderType): Type of the order.
        quantity (int): Ordered quantity.
        limit_price (Optional[float]): Limit price for the order.
        stop_price (Optional[float]): Stop price for the order.
        status (OrderStatus): Current status.
        filled_quantity (int): Number of shares filled.
        avg_fill_price (float): Average execution price.
        created_at (datetime): Time of order creation.
        filled_at (Optional[datetime]): Time of order execution.
        tiger_order_id (Optional[str]): Tiger's internal order ID.
    """
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
    tiger_order_id: Optional[str] = None

    @property
    def is_active(self) -> bool:
        """Check if the order is still active (not filled, cancelled, or rejected).

        Returns:
            bool: True if active, False otherwise.
        """
        return self.status in (OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED)


class PaperTrader:
    """Paper trading engine that executes orders via Tiger Open API
    in sandbox mode with local P&L tracking.
    """

    def __init__(self, tiger_id: str = TIGER_ID, account_id: str = ACCOUNT_ID,
                 private_key_path: str = PRIVATE_KEY_PATH,
                 sandbox: bool = SANDBOX_MODE,
                 max_position_size: float = MAX_POSITION_SIZE,
                 daily_loss_limit: float = DAILY_LOSS_LIMIT) -> None:
        """Initialize paper trader.

        Args:
            tiger_id (str): Tiger developer ID.
            account_id (str): Tiger account ID.
            private_key_path (str): Path to RSA private key.
            sandbox (bool): True for paper trading, False for live.
            max_position_size (float): Maximum USD per position.
            daily_loss_limit (float): Stop trading if daily loss exceeds this.
        """
        self.tiger_id = tiger_id
        self.account_id = account_id
        self.private_key_path = private_key_path
        self.sandbox = sandbox
        self.max_position_size = max_position_size
        self.daily_loss_limit = daily_loss_limit

        self._trade_client: Optional[TradeClient] = None
        self._connected: bool = False

        self._positions: Dict[str, Position] = {}
        self._orders: Dict[str, OrderRecord] = {}
        self._daily_pnl: float = 0.0
        self._initial_balance: Optional[float] = None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def connect(self) -> bool:
        """Connect to Tiger Open API with retry logic.

        Returns:
            bool: True if connection is successful.
        """
        try:
            client_config = TigerOpenClientConfig(sandbox_debug=self.sandbox)
            client_config.private_key = read_private_key(self.private_key_path)
            client_config.tiger_id = self.tiger_id
            client_config.account = self.account_id

            self._trade_client = TradeClient(client_config)

            account_info = self._trade_client.get_account_info(self.account_id)
            self._initial_balance = account_info.get('net_liquidation', 0.0)

            self._connected = True
            logger.info("✅ Paper trader connected to Tiger API")
            logger.info(f"   Account: {self.account_id}")
            logger.info(f"   Initial balance: ${self._initial_balance:,.2f}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect paper trader: {e}")
            raise  # trigger tenacity retry

    def disconnect(self) -> None:
        """Disconnect from API."""
        self._connected = False
        logger.info("Paper trader disconnected")

    def is_connected(self) -> bool:
        """Check if trader is connected.

        Returns:
            bool: Connection status.
        """
        return self._connected

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    def get_account_summary(self) -> Dict[str, Any]:
        """Get full account summary including balance and positions.

        Returns:
            Dict[str, Any]: Dictionary of account summary details.
        """
        if not self._trade_client:
            raise RuntimeError("Not connected")

        try:
            info = self._trade_client.get_account_info(self.account_id)
            positions = self._trade_client.get_positions(self.account_id)

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

    @lru_cache(maxsize=1)
    def _get_cached_tiger_positions(self) -> Any:
        """Cached wrapper around Tiger API position fetch to save memory and API calls."""
        if not self._trade_client:
            raise RuntimeError("Not connected")
        return self._trade_client.get_positions(self.account_id)

    def get_positions(self, use_cache: bool = False) -> Dict[str, Position]:
        """Get current positions, optionally using LRU cache.

        Args:
            use_cache (bool): Whether to use the cached position result.
            
        Returns:
            Dict[str, Position]: Dictionary of current open positions.
        """
        if not self._trade_client:
            raise RuntimeError("Not connected")

        try:
            if use_cache:
                tiger_positions = self._get_cached_tiger_positions()
            else:
                tiger_positions = self._trade_client.get_positions(self.account_id)
                self._get_cached_tiger_positions.cache_clear()  # reset cache
                
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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    def place_order(self, symbol: str, side: OrderSide, quantity: int,
                    order_type: OrderType = OrderType.MARKET,
                    limit_price: Optional[float] = None,
                    stop_price: Optional[float] = None) -> OrderRecord:
        """Place a new order with retry logic.

        Args:
            symbol (str): Ticker symbol.
            side (OrderSide): BUY or SELL.
            quantity (int): Number of shares/contracts.
            order_type (OrderType): MARKET, LIMIT, STOP, STOP_LIMIT.
            limit_price (Optional[float]): Required for LIMIT and STOP_LIMIT orders.
            stop_price (Optional[float]): Required for STOP and STOP_LIMIT orders.

        Returns:
            OrderRecord: The tracked order record.
        """
        if not self._connected:
            raise RuntimeError("Trader not connected")

        if not self._validate_order(symbol, side, quantity, order_type, limit_price, stop_price):
            raise ValueError("Order failed validation")

        order = OrderRecord(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price
        )

        try:
            contract = Contract()
            contract.symbol = symbol
            contract.sec_type = "STK"
            contract.exchange = "US" if SANDBOX_MODE else "US"

            tiger_order = Order()
            tiger_order.account = self.account_id
            tiger_order.contract = contract
            tiger_order.order_type = order_type.value
            tiger_order.quantity = quantity

            if limit_price is not None:
                tiger_order.limit_price = limit_price
            if stop_price is not None:
                tiger_order.stop_price = stop_price

            tiger_order.action = side.value

            tiger_order_id = self._trade_client.place_order(tiger_order)
            order.tiger_order_id = tiger_order_id
            order.status = OrderStatus.PENDING

            self._orders[order.id] = order
            logger.info(f"📤 Order placed: {side.value} {quantity} {symbol} "
                       f"({order_type.value}) - ID: {tiger_order_id}")
            return order

        except Exception as e:
            logger.error(f"❌ Order placement failed: {e}")
            order.status = OrderStatus.REJECTED
            self._orders[order.id] = order
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order with retry logic.

        Args:
            order_id (str): Internal order ID to cancel.

        Returns:
            bool: True if cancellation succeeded, False otherwise.
        """
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
            raise

    def update_order(self, tiger_order_id: str, status: str, filled_qty: int, avg_price: float) -> None:
        """Update order status locally (e.g., from WebSocket).

        Args:
            tiger_order_id (str): Tiger's order ID.
            status (str): New status (from Tiger).
            filled_qty (int): Quantity filled.
            avg_price (float): Average fill price.
        """
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

        if old_status != OrderStatus.FILLED and order.status == OrderStatus.FILLED:
            self._on_order_filled(order)

        logger.debug(f"Order {tiger_order_id} updated: {status}")

    def _on_order_filled(self, order: OrderRecord) -> None:
        """Handle order fill event.

        Args:
            order (OrderRecord): The filled order record.
        """
        logger.info(f"✅ Order filled: {order.symbol} {order.quantity} @ ${order.avg_fill_price:.2f}")

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
            total_quantity = pos.quantity + order.quantity
            total_cost = (pos.avg_cost * pos.quantity) + (order.avg_fill_price * order.quantity)
            pos.quantity = total_quantity
            pos.avg_cost = total_cost / total_quantity if total_quantity > 0 else 0
            pos.side = OrderSide.BUY
        else:
            pos.quantity -= order.quantity
            if pos.quantity <= 0:
                realized_pnl = (order.avg_fill_price - pos.avg_cost) * order.quantity
                self._daily_pnl += realized_pnl
                logger.info(f"💰 Position closed: {symbol} P&L: ${realized_pnl:.2f}")
                if pos.quantity == 0:
                    self._positions.pop(symbol, None)
                    return

        pos.current_price = order.avg_fill_price
        pos.update_price(order.avg_fill_price)

    def _validate_order(self, symbol: str, side: OrderSide, quantity: int,
                        order_type: OrderType, limit_price: Optional[float],
                        stop_price: Optional[float]) -> bool:
        """Validate order parameters before submission.

        Args:
            symbol (str): Ticker symbol.
            side (OrderSide): BUY or SELL.
            quantity (int): Number of shares/contracts.
            order_type (OrderType): Type of order.
            limit_price (Optional[float]): Limit price if applicable.
            stop_price (Optional[float]): Stop price if applicable.

        Returns:
            bool: True if valid, False otherwise.
        """
        if quantity <= 0:
            logger.error("Quantity must be positive")
            return False

        if order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and limit_price is None:
            logger.error(f"{order_type.value} order requires limit_price")
            return False

        if order_type in (OrderType.STOP, OrderType.STOP_LIMIT) and stop_price is None:
            logger.error(f"{order_type.value} order requires stop_price")
            return False

        if side == OrderSide.BUY:
            estimated_cost = limit_price if limit_price else 100.0  # placeholder
            if estimated_cost * quantity > self.max_position_size:
                logger.error(f"Order size exceeds max position limit: ${estimated_cost * quantity:,.2f} > ${self.max_position_size:,.2f}")
                return False

        if self._daily_pnl < -self.daily_loss_limit:
            logger.error(f"Daily loss limit reached: ${self._daily_pnl:.2f}")
            return False

        return True

    def get_active_orders(self) -> List[OrderRecord]:
        """Get all active orders.

        Returns:
            List[OrderRecord]: List of active orders.
        """
        return [o for o in self._orders.values() if o.is_active]

    def get_order_history(self) -> List[OrderRecord]:
        """Get all order history.

        Returns:
            List[OrderRecord]: List of all orders.
        """
        return list(self._orders.values())

    def get_open_positions(self) -> Dict[str, Position]:
        """Get current open positions locally tracked.

        Returns:
            Dict[str, Position]: Dictionary of open positions.
        """
        return self._positions.copy()

    def get_daily_pnl(self) -> float:
        """Get today's realized P&L.

        Returns:
            float: Today's P&L.
        """
        return self._daily_pnl
