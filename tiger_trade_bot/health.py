"""
Health check endpoints for Tiger Trade Bot.

Three levels:
- /health/live: process is running (no dependencies)
- /health/ready: app is ready to serve (Tiger API connected)
- /health/detail: full status (account, positions, metrics)
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from config import HEALTH_PORT
from .trader import PaperTrader
from .data import TigerDataFetcher


class HealthService:
    """Health service that maintains references to core components."""

    def __init__(self) -> None:
        self.trader: Optional[PaperTrader] = None
        self.data_fetcher: Optional[TigerDataFetcher] = None
        self.start_time: datetime = datetime.utcnow()
        self._app: Optional[FastAPI] = None

    def set_components(self, trader: PaperTrader, data_fetcher: TigerDataFetcher) -> None:
        """Set references to core components for health checks."""
        self.trader = trader
        self.data_fetcher = data_fetcher

    def create_app(self) -> FastAPI:
        """Create FastAPI app with health endpoints."""
        self._app = FastAPI(title="Tiger Trade Bot Health", version="1.0")
        self._app.get("/health/live")(self.live)
        self._app.get("/health/ready")(self.ready)
        self._app.get("/health/detail")(self.detail)
        return self._app

    async def live(self) -> Dict[str, str]:
        """Liveness probe - simply returns if process is alive."""
        return {"status": "alive", "timestamp": datetime.utcnow().isoformat() + "Z"}

    async def ready(self) -> JSONResponse:
        """Readiness probe - checks if Tiger API is connected."""
        if not self.trader or not self.trader.is_connected():
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "reason": "trader_not_connected",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            )
        return JSONResponse(
            status_code=200,
            content={
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )

    async def detail(self) -> Dict[str, Any]:
        """Detailed status with account, positions, orders."""
        detail: Dict[str, Any] = {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
        }

        if self.trader and self.trader.is_connected():
            try:
                summary = self.trader.get_account_summary()
                detail["account"] = {
                    "net_liquidation": summary.get("net_liquidation"),
                    "cash_balance": summary.get("cash_balance"),
                    "daily_pnl": summary.get("daily_pnl"),
                }
                positions = self.trader.get_positions()
                detail["positions"] = {
                    "count": len(positions),
                    "symbols": list(positions.keys()),
                }
                active_orders = self.trader.get_active_orders()
                detail["orders"] = {
                    "active_count": len(active_orders),
                }
            except Exception as e:
                detail["error"] = str(e)
                detail["status"] = "degraded"
        else:
            detail["trader"] = "disconnected"

        return detail


_health_service: Optional[HealthService] = None


def get_health_service() -> HealthService:
    """Singleton health service."""
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
    return _health_service


async def run_health_server() -> None:
    """Run the health server (called from bot main)."""
    service = get_health_service()
    app = service.create_app()
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=HEALTH_PORT,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    await server.serve()


def start_health_server_in_thread(trader: PaperTrader, data_fetcher: TigerDataFetcher) -> None:
    """
    Start health server in a background thread.
    Must be called before the main bot loop.
    """
    import threading

    service = get_health_service()
    service.set_components(trader, data_fetcher)

    thread = threading.Thread(
        target=lambda: asyncio.run(run_health_server()),
        daemon=True,
        name="HealthServer"
    )
    thread.start()
    print(f"Health server started on port {HEALTH_PORT}")
