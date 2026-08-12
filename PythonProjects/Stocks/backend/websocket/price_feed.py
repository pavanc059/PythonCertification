"""
WebSocket price feed — WS /ws/prices?token=<jwt>

Streams live price updates to authenticated clients.  Clients subscribe to
a list of tickers; the server broadcasts fresh prices every 30 seconds using
yfinance, then sends only the tickers each connection has subscribed to.

Message protocol (JSON)
-----------------------
Client → Server:
  {"type": "subscribe",   "tickers": ["AAPL", "MSFT"]}
  {"type": "unsubscribe", "tickers": ["AAPL"]}

Server → Client:
  {"type": "prices", "data": {"AAPL": 192.40, "MSFT": 430.10}}
  {"type": "error",  "message": "Authentication failed"}
  {"type": "ack",    "message": "Subscribed to AAPL, MSFT"}
  {"type": "ack",    "message": "Unsubscribed from AAPL"}

Requirements: R8.1, R8.2, R8.3, R8.4, R8.5
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError

logger = logging.getLogger(__name__)

# How often (in seconds) to push price updates to clients (R8.5).
PRICE_BROADCAST_INTERVAL: int = 30

router = APIRouter()


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Manages active WebSocket connections and per-connection subscriptions."""

    def __init__(self) -> None:
        # Map connection_id → WebSocket
        self.connections: Dict[str, WebSocket] = {}
        # Map connection_id → set of subscribed tickers (uppercased)
        self.subscriptions: Dict[str, Set[str]] = {}

    async def connect(self, connection_id: str, ws: WebSocket) -> None:
        """Accept the WebSocket and register the connection."""
        await ws.accept()
        self.connections[connection_id] = ws
        self.subscriptions[connection_id] = set()
        logger.info("WS connected: %s", connection_id)

    def disconnect(self, connection_id: str) -> None:
        """Remove a connection and its subscriptions."""
        self.connections.pop(connection_id, None)
        self.subscriptions.pop(connection_id, None)
        logger.info("WS disconnected: %s", connection_id)

    def subscribe(self, connection_id: str, tickers: list) -> None:
        """Add *tickers* to the subscription set for *connection_id*."""
        if connection_id not in self.subscriptions:
            return
        normalized = {t.upper() for t in tickers if isinstance(t, str)}
        self.subscriptions[connection_id].update(normalized)

    def unsubscribe(self, connection_id: str, tickers: list) -> None:
        """Remove *tickers* from the subscription set for *connection_id*."""
        if connection_id not in self.subscriptions:
            return
        normalized = {t.upper() for t in tickers if isinstance(t, str)}
        self.subscriptions[connection_id].difference_update(normalized)

    def get_all_tickers(self) -> Set[str]:
        """Return the union of all subscribed tickers across every connection."""
        result: Set[str] = set()
        for tickers in self.subscriptions.values():
            result.update(tickers)
        return result

    async def broadcast_prices(self, prices: Dict[str, float]) -> None:
        """
        Send each connection only the prices for its subscribed tickers.

        Silently skips connections that have already been closed; cleans up
        any connections where the send itself raises an exception.
        """
        dead: list[str] = []
        for conn_id, ws in list(self.connections.items()):
            subscribed = self.subscriptions.get(conn_id, set())
            if not subscribed:
                continue
            # Filter prices to only the tickers this connection cares about.
            filtered = {t: p for t, p in prices.items() if t in subscribed}
            if not filtered:
                continue
            try:
                await ws.send_text(json.dumps({"type": "prices", "data": filtered}))
            except Exception:
                # Client already disconnected; mark for cleanup.
                dead.append(conn_id)
        for conn_id in dead:
            self.disconnect(conn_id)


# Singleton manager shared across all WebSocket connections in this process.
manager = ConnectionManager()


# ---------------------------------------------------------------------------
# yfinance price fetcher
# ---------------------------------------------------------------------------


async def fetch_batch_prices(tickers: Set[str]) -> Dict[str, float]:
    """
    Fetch current prices for all *tickers* using yfinance.

    Runs yfinance in a thread pool so the event loop is not blocked.
    Returns ``{ticker: price}``; returns an empty dict on any error.
    """
    if not tickers:
        return {}

    def _fetch_sync() -> Dict[str, float]:
        import yfinance as yf  # deferred import — optional dependency at test time

        prices: Dict[str, float] = {}
        ticker_list = list(tickers)

        try:
            # Prefer fast_info.last_price (lightweight; one request per ticker
            # but still faster than full .info).  Fall back to .info for tickers
            # where fast_info is unavailable.
            for t in ticker_list:
                try:
                    obj = yf.Ticker(t)
                    price = None
                    try:
                        price = obj.fast_info.last_price
                    except Exception:
                        pass
                    if price is None:
                        info = obj.info or {}
                        price = info.get("regularMarketPrice") or info.get("currentPrice")
                    if price is not None:
                        prices[t] = float(price)
                except Exception as exc:
                    logger.debug("Price fetch error for %s: %s", t, exc)
        except Exception as exc:
            logger.warning("Batch price fetch failed: %s", exc)

        return prices

    try:
        return await asyncio.to_thread(_fetch_sync)
    except Exception as exc:
        logger.warning("asyncio.to_thread price fetch failed: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Background broadcast loop
# ---------------------------------------------------------------------------


async def _price_broadcast_loop(connection_id: str) -> None:
    """
    Runs as a background task for a single connection.

    Every PRICE_BROADCAST_INTERVAL seconds, fetches prices for all currently
    subscribed tickers (union across *all* connections for efficiency) and
    calls manager.broadcast_prices().

    Exits cleanly when the connection is no longer tracked.
    """
    while connection_id in manager.connections:
        await asyncio.sleep(PRICE_BROADCAST_INTERVAL)
        # Check again after sleeping — connection may have closed.
        if connection_id not in manager.connections:
            break
        all_tickers = manager.get_all_tickers()
        if all_tickers:
            prices = await fetch_batch_prices(all_tickers)
            if prices:
                await manager.broadcast_prices(prices)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket, token: str = "") -> None:
    """
    WebSocket endpoint for real-time price updates (R8.1).

    Flow
    ----
    1. Validate the ``?token=`` JWT query parameter.
    2. Accept the connection and start the 30-second broadcast loop.
    3. Listen for subscribe / unsubscribe messages from the client.
    4. On WebSocketDisconnect or any error, cancel the broadcast task and
       clean up the connection.
    """
    from auth.service import decode_token
    from config import settings

    # -- 1. Authenticate before accepting the connection. ------------------
    # WebSocket protocol requires accept() before sending any message, so we
    # accept first, send the error, then close — as required by the spec.
    try:
        token_data = decode_token(token, settings.secret_key)
    except (JWTError, Exception):
        # Accept so we can send the error frame, then close.
        await websocket.accept()
        await websocket.send_text(
            json.dumps({"type": "error", "message": "Authentication failed"})
        )
        await websocket.close(code=1008)  # 1008 = Policy Violation
        return

    # -- 2. Register connection. -------------------------------------------
    connection_id = str(uuid.uuid4())
    await manager.connect(connection_id, websocket)
    logger.info(
        "WS authenticated: user_id=%s connection=%s",
        token_data.user_id,
        connection_id,
    )

    # -- 3. Start background price broadcast loop. -------------------------
    broadcast_task = asyncio.create_task(_price_broadcast_loop(connection_id))

    # -- 4. Message receive loop. ------------------------------------------
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                # Malformed JSON — ignore and stay connected.
                logger.debug("WS %s: invalid JSON received, ignoring.", connection_id)
                continue

            msg_type = msg.get("type")
            tickers_raw = msg.get("tickers", [])

            if msg_type == "subscribe":
                tickers = [t for t in tickers_raw if isinstance(t, str)]
                if tickers:
                    manager.subscribe(connection_id, tickers)
                    ack_list = ", ".join(t.upper() for t in tickers)
                    await websocket.send_text(
                        json.dumps({"type": "ack", "message": f"Subscribed to {ack_list}"})
                    )
                    # Send an immediate price snapshot so the client doesn't
                    # have to wait up to 30 seconds for the first update.
                    subscribed_tickers = manager.subscriptions.get(connection_id, set())
                    if subscribed_tickers:
                        prices = await fetch_batch_prices(subscribed_tickers)
                        if prices:
                            filtered = {
                                t: p
                                for t, p in prices.items()
                                if t in subscribed_tickers
                            }
                            if filtered:
                                await websocket.send_text(
                                    json.dumps({"type": "prices", "data": filtered})
                                )

            elif msg_type == "unsubscribe":
                tickers = [t for t in tickers_raw if isinstance(t, str)]
                if tickers:
                    manager.unsubscribe(connection_id, tickers)
                    ack_list = ", ".join(t.upper() for t in tickers)
                    await websocket.send_text(
                        json.dumps({"type": "ack", "message": f"Unsubscribed from {ack_list}"})
                    )
            else:
                # Unknown message type — silently ignore (stays connected).
                logger.debug("WS %s: unknown message type '%s'.", connection_id, msg_type)

    except WebSocketDisconnect:
        logger.info("WS %s: client disconnected normally.", connection_id)
    except Exception as exc:
        logger.warning("WS %s: unexpected error: %s", connection_id, exc)
    finally:
        # -- 5. Clean up. --------------------------------------------------
        broadcast_task.cancel()
        try:
            await broadcast_task
        except (asyncio.CancelledError, Exception):
            pass
        manager.disconnect(connection_id)
