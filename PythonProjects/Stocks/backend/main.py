"""
StockIQ FastAPI Backend
Main application entry point with CORS configuration and router setup.
"""

import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Settings live in config.py so that dependencies.py and auth/ can import
# them without creating a circular-import chain through main.py.
from config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Tradewell API",
    version="2.0",
    description="FastAPI backend for Tradewell — AI-powered trading intelligence with autopilot, predictions, and real-time market data.",
)

# CORS — allow the React dev server (Vite on 5173) and prod build (Nginx on 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from auth.router import router as auth_router
app.include_router(auth_router, prefix="/auth", tags=["auth"])

from portfolio.router import router as portfolio_router
app.include_router(portfolio_router, prefix="/portfolio", tags=["portfolio"])

from trading.router import router as trading_router
app.include_router(trading_router, prefix="/trading", tags=["trading"])

from watchlist.router import router as watchlist_router
app.include_router(watchlist_router, prefix="/watchlist", tags=["watchlist"])

from market.router import router as market_router
app.include_router(market_router, prefix="/market", tags=["market"])

from settings.router import router as settings_router
app.include_router(settings_router, prefix="/api/v1/settings", tags=["settings"])

from websocket.price_feed import router as ws_router
app.include_router(ws_router, tags=["websocket"])

from ai.router import router as ai_router
app.include_router(ai_router, prefix="/ai", tags=["ai"])

from autotrade.router import router as autotrade_router
app.include_router(autotrade_router, prefix="/autotrade", tags=["autotrade"])

from autopilot.router import router as autopilot_router
app.include_router(autopilot_router, prefix="/autopilot", tags=["autopilot"])


# ---------------------------------------------------------------------------
# Webull session management
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def _startup_webull() -> None:
    """Initialise the WebullClient singleton on application startup.

    - Skips Webull initialisation when ``market_data_source`` is
      ``"yfinance"`` or ``"stub"`` (Requirements 13.1, 13.4).
    - When ``"webull"``: instantiates ``WebullClient`` from settings
      (app_key, app_secret, region_id, endpoint).
      NO login() call — the official SDK signs every request automatically
      via HMAC-SHA1.  NO background refresh task — no session to refresh.

    The client instance is stored in ``state._webull_client`` via
    ``state.set_webull_client()`` to avoid circular imports with routers.

    Requirements: 13.1, 13.2, 13.3
    """
    from state import set_webull_client

    if settings.market_data_source in ("yfinance", "stub"):
        logger.info(
            "market_data_source=%r — skipping Webull initialisation.",
            settings.market_data_source,
        )
        return

    # market_data_source == "webull"
    from webull_client.client import WebullClient
    from webull.core.exception.exceptions import ServerException

    endpoint = (
        "api.sandbox.webull.com"
        if settings.webull_sandbox
        else settings.webull_endpoint
    )
    try:
        client = WebullClient(
            app_key=settings.webull_app_key,
            app_secret=settings.webull_app_secret,
            region_id=settings.webull_region_id,
            endpoint=endpoint,
        )
        set_webull_client(client)
        logger.info(
            "WebullClient constructed for region=%s endpoint=%s",
            settings.webull_region_id, endpoint,
        )
    except ServerException as exc:
        logger.warning(
            "Webull initialisation failed (%s %s) — market data via Webull will be "
            "unavailable. Check WEBULL_APP_KEY / WEBULL_APP_SECRET in your .env.",
            exc.http_status, exc.error_code,
        )
    # No login(), no asyncio.create_task — SDK signs every request automatically.


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Liveness probe — returns API version and status."""
    return {"status": "ok", "version": "2.0"}


# ---------------------------------------------------------------------------
# Uvicorn entry point (python main.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
