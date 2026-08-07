"""
WebSocket streaming for real-time market data.

Implements WebSocket connections with automatic reconnection and
sub-500ms latency for real-time price updates (Requirement 12.1).
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urlparse

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketClientProtocol = Any

from ..models import Price

logger = logging.getLogger(__name__)


class StreamStatus(str, Enum):
    """WebSocket connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    CLOSED = "closed"


@dataclass
class ConnectionConfig:
    """WebSocket connection configuration."""
    url: str
    auth: Optional[Dict[str, Any]] = None
    ping_interval: int = 20  # seconds
    ping_timeout: int = 10  # seconds
    max_reconnect_attempts: int = 5
    reconnect_delay: float = 1.0  # seconds, exponential backoff base
    max_reconnect_delay: float = 60.0  # seconds
    latency_target_ms: int = 500  # Requirement 12.1: sub-500ms latency
    
    def __post_init__(self):
        """Validate configuration."""
        parsed = urlparse(self.url)
        if parsed.scheme not in ('ws', 'wss'):
            raise ValueError(f"Invalid WebSocket URL scheme: {parsed.scheme}")


@dataclass
class LatencyMetrics:
    """Latency tracking metrics."""
    message_count: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0
    over_target_count: int = 0
    
    def record(self, latency_ms: float, target_ms: int):
        """Record a latency measurement."""
        self.message_count += 1
        self.total_latency_ms += latency_ms
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)
        if latency_ms > target_ms:
            self.over_target_count += 1
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.message_count == 0:
            return 0.0
        return self.total_latency_ms / self.message_count
    
    @property
    def success_rate(self) -> float:
        """Calculate percentage of messages meeting latency target."""
        if self.message_count == 0:
            return 100.0
        return ((self.message_count - self.over_target_count) / self.message_count) * 100


class WebSocketStream:
    """
    WebSocket client for real-time market data streaming.
    
    Features:
    - Automatic reconnection with exponential backoff
    - Message latency tracking (Requirement 12.1: sub-500ms)
    - Multiple channel subscriptions
    - Connection pooling support
    - Graceful shutdown
    
    Example:
        ```python
        config = ConnectionConfig(url="wss://stream.example.com")
        stream = WebSocketStream(config)
        
        async def price_handler(data: Dict):
            price = Price.from_dict(data)
            print(f"Received: {price}")
        
        await stream.connect()
        await stream.subscribe(["AAPL", "TSLA"], price_handler)
        await stream.run()  # Run until closed
        ```
    """
    
    def __init__(self, config: ConnectionConfig):
        """
        Initialize WebSocket stream.
        
        Args:
            config: Connection configuration
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets library required for real-time streaming. "
                "Install with: pip install websockets"
            )
        
        self.config = config
        self.status = StreamStatus.DISCONNECTED
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.reconnect_attempts = 0
        self.latency_metrics = LatencyMetrics()
        self._running = False
        self._tasks: Set[asyncio.Task] = set()
        
        logger.info(f"Initialized WebSocketStream for {config.url}")
    
    async def connect(self) -> None:
        """
        Establish WebSocket connection.
        
        Implements automatic reconnection with exponential backoff
        on connection failure.
        
        Raises:
            ConnectionError: If max reconnect attempts exceeded
        """
        if self.status == StreamStatus.CONNECTED:
            logger.warning("Already connected")
            return
        
        self.status = StreamStatus.CONNECTING
        
        while self.reconnect_attempts < self.config.max_reconnect_attempts:
            try:
                logger.info(
                    f"Connecting to {self.config.url} "
                    f"(attempt {self.reconnect_attempts + 1}/"
                    f"{self.config.max_reconnect_attempts})"
                )
                
                # Establish connection with timeout and ping/pong
                self.websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.config.url,
                        ping_interval=self.config.ping_interval,
                        ping_timeout=self.config.ping_timeout,
                    ),
                    timeout=10.0  # 10 second connection timeout
                )
                
                self.status = StreamStatus.CONNECTED
                self.reconnect_attempts = 0
                logger.info(f"Connected to {self.config.url}")
                
                # Authenticate if required
                if self.config.auth:
                    await self._authenticate()
                
                # Resubscribe to channels after reconnection
                if self.subscriptions:
                    await self._resubscribe()
                
                return
                
            except (asyncio.TimeoutError, OSError) as e:
                self.reconnect_attempts += 1
                logger.warning(
                    f"Connection failed (attempt {self.reconnect_attempts}): {e}"
                )
                
                if self.reconnect_attempts >= self.config.max_reconnect_attempts:
                    self.status = StreamStatus.ERROR
                    raise ConnectionError(
                        f"Failed to connect after {self.config.max_reconnect_attempts} attempts"
                    )
                
                # Exponential backoff with max delay cap
                delay = min(
                    self.config.reconnect_delay * (2 ** (self.reconnect_attempts - 1)),
                    self.config.max_reconnect_delay
                )
                logger.info(f"Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
    
    async def _authenticate(self) -> None:
        """Send authentication message if configured."""
        if not self.websocket or not self.config.auth:
            return
        
        auth_message = json.dumps({
            "action": "authenticate",
            **self.config.auth
        })
        
        await self.websocket.send(auth_message)
        logger.info("Sent authentication message")
    
    async def _resubscribe(self) -> None:
        """Resubscribe to all channels after reconnection."""
        if not self.subscriptions:
            return
        
        logger.info(f"Resubscribing to {len(self.subscriptions)} channels")
        
        for channel in self.subscriptions.keys():
            await self._send_subscription(channel, subscribe=True)
    
    async def subscribe(
        self,
        channels: List[str],
        callback: Optional[Callable[[Dict], None]] = None
    ) -> None:
        """
        Subscribe to data channels.
        
        Args:
            channels: List of channel identifiers (e.g., ticker symbols)
            callback: Optional callback function for received messages
        
        Example:
            ```python
            async def handler(data):
                print(f"Price update: {data}")
            
            await stream.subscribe(["AAPL", "TSLA"], handler)
            ```
        """
        if not self.websocket or self.status != StreamStatus.CONNECTED:
            raise RuntimeError("Not connected. Call connect() first.")
        
        for channel in channels:
            # Add callback to subscription registry
            if channel not in self.subscriptions:
                self.subscriptions[channel] = []
            
            if callback:
                self.subscriptions[channel].append(callback)
            
            # Send subscription message
            await self._send_subscription(channel, subscribe=True)
        
        logger.info(f"Subscribed to channels: {channels}")
    
    async def unsubscribe(self, channels: List[str]) -> None:
        """
        Unsubscribe from data channels.
        
        Args:
            channels: List of channel identifiers to unsubscribe from
        """
        if not self.websocket or self.status != StreamStatus.CONNECTED:
            logger.warning("Not connected, cannot unsubscribe")
            return
        
        for channel in channels:
            if channel in self.subscriptions:
                del self.subscriptions[channel]
                await self._send_subscription(channel, subscribe=False)
        
        logger.info(f"Unsubscribed from channels: {channels}")
    
    async def _send_subscription(self, channel: str, subscribe: bool) -> None:
        """Send subscription/unsubscription message."""
        if not self.websocket:
            return
        
        message = json.dumps({
            "action": "subscribe" if subscribe else "unsubscribe",
            "channel": channel
        })
        
        await self.websocket.send(message)
    
    async def handle_message(self, message: Dict[str, Any]) -> None:
        """
        Process incoming WebSocket message.
        
        Calculates latency and invokes registered callbacks.
        
        Args:
            message: Parsed message data
        """
        # Calculate latency if timestamp present
        if 'timestamp' in message:
            try:
                msg_timestamp = datetime.fromisoformat(message['timestamp'])
                latency_ms = (datetime.utcnow() - msg_timestamp).total_seconds() * 1000
                self.latency_metrics.record(latency_ms, self.config.latency_target_ms)
                
                # Log warning if latency exceeds target
                if latency_ms > self.config.latency_target_ms:
                    logger.warning(
                        f"Latency {latency_ms:.1f}ms exceeds target "
                        f"{self.config.latency_target_ms}ms"
                    )
            except (ValueError, KeyError) as e:
                logger.debug(f"Could not parse timestamp: {e}")
        
        # Route message to channel handlers
        channel = message.get('channel') or message.get('symbol')
        if channel and channel in self.subscriptions:
            for callback in self.subscriptions[channel]:
                try:
                    # Support both sync and async callbacks
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message)
                    else:
                        callback(message)
                except Exception as e:
                    logger.error(f"Error in callback for {channel}: {e}", exc_info=True)
    
    async def run(self) -> None:
        """
        Run the WebSocket message loop.
        
        Continuously receives and processes messages until
        the connection is closed or an error occurs.
        
        Automatically attempts reconnection on unexpected disconnects.
        """
        self._running = True
        
        while self._running:
            if not self.websocket or self.status != StreamStatus.CONNECTED:
                logger.info("Not connected, attempting to connect...")
                try:
                    await self.connect()
                except ConnectionError as e:
                    logger.error(f"Connection failed: {e}")
                    await asyncio.sleep(self.config.max_reconnect_delay)
                    continue
            
            try:
                # Receive message with timeout
                raw_message = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=self.config.ping_interval + self.config.ping_timeout
                )
                
                # Parse and handle message
                try:
                    message = json.loads(raw_message)
                    await self.handle_message(message)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                    
            except asyncio.TimeoutError:
                logger.warning("Receive timeout, connection may be stale")
                await self._reconnect()
                
            except websockets.ConnectionClosed as e:
                logger.warning(f"Connection closed: {e}")
                await self._reconnect()
                
            except Exception as e:
                logger.error(f"Unexpected error in message loop: {e}", exc_info=True)
                await self._reconnect()
    
    async def _reconnect(self) -> None:
        """Attempt to reconnect after connection loss."""
        if self.status == StreamStatus.RECONNECTING:
            return  # Already reconnecting
        
        self.status = StreamStatus.RECONNECTING
        logger.info("Attempting to reconnect...")
        
        # Close existing connection
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.debug(f"Error closing websocket: {e}")
        
        self.websocket = None
        
        # Reconnect
        try:
            await self.connect()
        except ConnectionError as e:
            logger.error(f"Reconnection failed: {e}")
            self.status = StreamStatus.ERROR
    
    async def close(self) -> None:
        """
        Gracefully close the WebSocket connection.
        
        Unsubscribes from all channels and closes the connection.
        """
        self._running = False
        
        # Unsubscribe from all channels
        if self.subscriptions:
            await self.unsubscribe(list(self.subscriptions.keys()))
        
        # Close connection
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
        
        # Cancel running tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        self.status = StreamStatus.CLOSED
        self.websocket = None
    
    def get_latency_metrics(self) -> Dict[str, Any]:
        """
        Get current latency metrics.
        
        Returns:
            Dictionary with latency statistics including:
            - avg_latency_ms: Average latency
            - min_latency_ms: Minimum latency
            - max_latency_ms: Maximum latency
            - success_rate: % of messages meeting target latency
            - message_count: Total messages processed
        """
        return {
            'avg_latency_ms': self.latency_metrics.avg_latency_ms,
            'min_latency_ms': self.latency_metrics.min_latency_ms,
            'max_latency_ms': self.latency_metrics.max_latency_ms,
            'success_rate': self.latency_metrics.success_rate,
            'message_count': self.latency_metrics.message_count,
            'over_target_count': self.latency_metrics.over_target_count,
            'target_ms': self.config.latency_target_ms,
        }
    
    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return (
            self.status == StreamStatus.CONNECTED and
            self.websocket is not None and
            not self.websocket.closed
        )
    
    def __repr__(self) -> str:
        return (
            f"WebSocketStream(url={self.config.url}, "
            f"status={self.status}, "
            f"subscriptions={len(self.subscriptions)})"
        )
