"""
Tests for WebSocket streaming functionality.

Tests cover:
- Connection establishment and reconnection
- Message handling and latency tracking
- Subscription management
- Error handling and graceful degradation
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from stockiq.data.streams.websocket import (
    WebSocketStream,
    StreamStatus,
    ConnectionConfig,
    LatencyMetrics,
    WEBSOCKETS_AVAILABLE
)


# Skip all tests if websockets not available
pytestmark = pytest.mark.skipif(
    not WEBSOCKETS_AVAILABLE,
    reason="websockets library not installed"
)


class TestConnectionConfig:
    """Test ConnectionConfig validation."""
    
    def test_valid_ws_url(self):
        """Test valid ws:// URL."""
        config = ConnectionConfig(url="ws://localhost:8000")
        assert config.url == "ws://localhost:8000"
    
    def test_valid_wss_url(self):
        """Test valid wss:// URL."""
        config = ConnectionConfig(url="wss://stream.example.com")
        assert config.url == "wss://stream.example.com"
    
    def test_invalid_url_scheme(self):
        """Test invalid URL scheme raises error."""
        with pytest.raises(ValueError, match="Invalid WebSocket URL scheme"):
            ConnectionConfig(url="http://localhost:8000")
    
    def test_default_values(self):
        """Test default configuration values."""
        config = ConnectionConfig(url="ws://localhost:8000")
        assert config.ping_interval == 20
        assert config.ping_timeout == 10
        assert config.max_reconnect_attempts == 5
        assert config.reconnect_delay == 1.0
        assert config.max_reconnect_delay == 60.0
        assert config.latency_target_ms == 500
    
    def test_custom_auth(self):
        """Test configuration with authentication."""
        auth = {"api_key": "test_key"}
        config = ConnectionConfig(url="wss://stream.example.com", auth=auth)
        assert config.auth == auth


class TestLatencyMetrics:
    """Test latency metrics tracking."""
    
    def test_initial_state(self):
        """Test initial metrics state."""
        metrics = LatencyMetrics()
        assert metrics.message_count == 0
        assert metrics.total_latency_ms == 0.0
        assert metrics.min_latency_ms == float('inf')
        assert metrics.max_latency_ms == 0.0
        assert metrics.over_target_count == 0
    
    def test_record_single_measurement(self):
        """Test recording a single latency measurement."""
        metrics = LatencyMetrics()
        metrics.record(150.0, 500)
        
        assert metrics.message_count == 1
        assert metrics.total_latency_ms == 150.0
        assert metrics.min_latency_ms == 150.0
        assert metrics.max_latency_ms == 150.0
        assert metrics.over_target_count == 0
    
    def test_record_multiple_measurements(self):
        """Test recording multiple measurements."""
        metrics = LatencyMetrics()
        metrics.record(100.0, 500)
        metrics.record(200.0, 500)
        metrics.record(600.0, 500)  # Over target
        
        assert metrics.message_count == 3
        assert metrics.min_latency_ms == 100.0
        assert metrics.max_latency_ms == 600.0
        assert metrics.over_target_count == 1
    
    def test_average_latency(self):
        """Test average latency calculation."""
        metrics = LatencyMetrics()
        metrics.record(100.0, 500)
        metrics.record(200.0, 500)
        metrics.record(300.0, 500)
        
        assert metrics.avg_latency_ms == 200.0
    
    def test_success_rate(self):
        """Test success rate calculation."""
        metrics = LatencyMetrics()
        metrics.record(100.0, 500)  # Success
        metrics.record(200.0, 500)  # Success
        metrics.record(600.0, 500)  # Over target
        metrics.record(700.0, 500)  # Over target
        
        assert metrics.success_rate == 50.0  # 2 out of 4
    
    def test_success_rate_no_messages(self):
        """Test success rate with no messages."""
        metrics = LatencyMetrics()
        assert metrics.success_rate == 100.0


class TestWebSocketStream:
    """Test WebSocketStream functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ConnectionConfig(
            url="ws://localhost:8000",
            max_reconnect_attempts=3,
            reconnect_delay=0.1,
            latency_target_ms=500
        )
    
    @pytest.fixture
    def stream(self, config):
        """Create WebSocketStream instance."""
        return WebSocketStream(config)
    
    def test_initialization(self, stream, config):
        """Test stream initialization."""
        assert stream.config == config
        assert stream.status == StreamStatus.DISCONNECTED
        assert stream.websocket is None
        assert stream.subscriptions == {}
        assert stream.reconnect_attempts == 0
        assert not stream._running
    
    def test_repr(self, stream):
        """Test string representation."""
        repr_str = repr(stream)
        assert "WebSocketStream" in repr_str
        assert "ws://localhost:8000" in repr_str
        assert "StreamStatus.DISCONNECTED" in repr_str or "disconnected" in repr_str.lower()
    
    @pytest.mark.asyncio
    async def test_connect_success(self, stream):
        """Test successful connection."""
        mock_websocket = AsyncMock()
        
        # Create async context manager mock for websockets.connect
        async def mock_connect_coro(*args, **kwargs):
            return mock_websocket
        
        with patch('stockiq.data.streams.websocket.websockets.connect', side_effect=mock_connect_coro):
            await stream.connect()
            
            assert stream.status == StreamStatus.CONNECTED
            assert stream.websocket == mock_websocket
            assert stream.reconnect_attempts == 0
    
    @pytest.mark.asyncio
    async def test_connect_with_auth(self, config):
        """Test connection with authentication."""
        config.auth = {"api_key": "test123"}
        stream = WebSocketStream(config)
        mock_websocket = AsyncMock()
        
        async def mock_connect_coro(*args, **kwargs):
            return mock_websocket
        
        with patch('stockiq.data.streams.websocket.websockets.connect', side_effect=mock_connect_coro):
            await stream.connect()
            
            # Should send auth message
            mock_websocket.send.assert_called_once()
            sent_data = json.loads(mock_websocket.send.call_args[0][0])
            assert sent_data['action'] == 'authenticate'
            assert sent_data['api_key'] == 'test123'
    
    @pytest.mark.asyncio
    async def test_connect_retry_on_failure(self, stream):
        """Test connection retry on failure."""
        mock_websocket = AsyncMock()
        call_count = 0
        
        # Create async function that fails twice, then succeeds
        async def mock_connect_with_retries(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.TimeoutError()
            elif call_count == 2:
                raise OSError("Connection refused")
            else:
                return mock_websocket
        
        with patch('stockiq.data.streams.websocket.websockets.connect', side_effect=mock_connect_with_retries):
            await stream.connect()
            
            assert stream.status == StreamStatus.CONNECTED
            assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_connect_max_retries_exceeded(self, stream):
        """Test connection failure after max retries."""
        with patch('stockiq.data.streams.websocket.websockets.connect') as mock_connect:
            mock_connect.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(ConnectionError, match="Failed to connect after"):
                await stream.connect()
            
            assert stream.status == StreamStatus.ERROR
            assert stream.reconnect_attempts == stream.config.max_reconnect_attempts
    
    @pytest.mark.asyncio
    async def test_subscribe_single_channel(self, stream):
        """Test subscribing to a single channel."""
        stream.websocket = AsyncMock()
        stream.status = StreamStatus.CONNECTED
        
        callback = Mock()
        await stream.subscribe(["AAPL"], callback)
        
        assert "AAPL" in stream.subscriptions
        assert callback in stream.subscriptions["AAPL"]
        stream.websocket.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_subscribe_multiple_channels(self, stream):
        """Test subscribing to multiple channels."""
        stream.websocket = AsyncMock()
        stream.status = StreamStatus.CONNECTED
        
        callback = Mock()
        await stream.subscribe(["AAPL", "TSLA", "MSFT"], callback)
        
        assert len(stream.subscriptions) == 3
        assert all(ticker in stream.subscriptions for ticker in ["AAPL", "TSLA", "MSFT"])
        assert stream.websocket.send.call_count == 3
    
    @pytest.mark.asyncio
    async def test_subscribe_not_connected(self, stream):
        """Test subscribing when not connected raises error."""
        with pytest.raises(RuntimeError, match="Not connected"):
            await stream.subscribe(["AAPL"])
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, stream):
        """Test unsubscribing from channels."""
        stream.websocket = AsyncMock()
        stream.status = StreamStatus.CONNECTED
        
        # First subscribe
        await stream.subscribe(["AAPL", "TSLA"])
        
        # Then unsubscribe
        await stream.unsubscribe(["AAPL"])
        
        assert "AAPL" not in stream.subscriptions
        assert "TSLA" in stream.subscriptions
    
    @pytest.mark.asyncio
    async def test_handle_message_with_callback(self, stream):
        """Test message handling invokes callback."""
        callback = Mock()
        stream.subscriptions["AAPL"] = [callback]
        
        message = {
            "channel": "AAPL",
            "price": 150.0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await stream.handle_message(message)
        
        callback.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_handle_message_async_callback(self, stream):
        """Test message handling with async callback."""
        async_callback = AsyncMock()
        stream.subscriptions["TSLA"] = [async_callback]
        
        message = {
            "channel": "TSLA",
            "price": 250.0
        }
        
        await stream.handle_message(message)
        
        async_callback.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_handle_message_latency_tracking(self, stream):
        """Test message latency tracking."""
        # Message from 300ms ago
        past_time = datetime.utcnow() - timedelta(milliseconds=300)
        message = {
            "channel": "AAPL",
            "timestamp": past_time.isoformat()
        }
        
        await stream.handle_message(message)
        
        assert stream.latency_metrics.message_count == 1
        # Latency should be approximately 300ms
        assert 250 <= stream.latency_metrics.avg_latency_ms <= 350
    
    @pytest.mark.asyncio
    async def test_handle_message_over_target_latency(self, stream, caplog):
        """Test warning when latency exceeds target."""
        # Message from 600ms ago (over 500ms target)
        past_time = datetime.utcnow() - timedelta(milliseconds=600)
        message = {
            "channel": "AAPL",
            "timestamp": past_time.isoformat()
        }
        
        await stream.handle_message(message)
        
        assert stream.latency_metrics.over_target_count == 1
        # Should log warning
        assert any("exceeds target" in record.message for record in caplog.records)
    
    @pytest.mark.asyncio
    async def test_handle_message_callback_error(self, stream, caplog):
        """Test error handling in callback doesn't crash handler."""
        def failing_callback(data):
            raise ValueError("Test error")
        
        stream.subscriptions["AAPL"] = [failing_callback]
        message = {"channel": "AAPL", "price": 150.0}
        
        # Should not raise
        await stream.handle_message(message)
        
        # Should log error
        assert any("Error in callback" in record.message for record in caplog.records)
    
    @pytest.mark.asyncio
    async def test_close_gracefully(self, stream):
        """Test graceful connection close."""
        stream.websocket = AsyncMock()
        stream.status = StreamStatus.CONNECTED
        stream._running = True
        stream.subscriptions = {"AAPL": [], "TSLA": []}
        
        await stream.close()
        
        assert not stream._running
        assert stream.status == StreamStatus.CLOSED
        assert stream.websocket is None
        assert len(stream.subscriptions) == 0
    
    def test_is_connected_property(self, stream):
        """Test is_connected property."""
        # Not connected initially
        assert not stream.is_connected
        
        # Connected
        stream.status = StreamStatus.CONNECTED
        stream.websocket = MagicMock(closed=False)
        assert stream.is_connected
        
        # Disconnected
        stream.websocket.closed = True
        assert not stream.is_connected
    
    def test_get_latency_metrics(self, stream):
        """Test getting latency metrics."""
        stream.latency_metrics.record(100.0, 500)
        stream.latency_metrics.record(200.0, 500)
        stream.latency_metrics.record(600.0, 500)
        
        metrics = stream.get_latency_metrics()
        
        assert metrics['message_count'] == 3
        assert metrics['avg_latency_ms'] == 300.0
        assert metrics['min_latency_ms'] == 100.0
        assert metrics['max_latency_ms'] == 600.0
        assert metrics['over_target_count'] == 1
        assert metrics['target_ms'] == 500
        assert 'success_rate' in metrics


class TestWebSocketStreamIntegration:
    """Integration tests for WebSocket stream."""
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test full connection lifecycle."""
        config = ConnectionConfig(
            url="ws://localhost:8000",
            max_reconnect_attempts=1
        )
        stream = WebSocketStream(config)
        mock_websocket = AsyncMock()
        mock_websocket.closed = False  # Ensure websocket is not marked as closed
        
        async def mock_connect_coro(*args, **kwargs):
            return mock_websocket
        
        with patch('stockiq.data.streams.websocket.websockets.connect', side_effect=mock_connect_coro):
            # Connect
            await stream.connect()
            assert stream.is_connected
            
            # Subscribe
            callback = Mock()
            await stream.subscribe(["AAPL"], callback)
            assert "AAPL" in stream.subscriptions
            
            # Handle message
            message = {"channel": "AAPL", "price": 150.0}
            await stream.handle_message(message)
            callback.assert_called_once()
            
            # Close
            await stream.close()
            assert not stream.is_connected
            assert stream.status == StreamStatus.CLOSED
    
    @pytest.mark.asyncio
    async def test_reconnection_preserves_subscriptions(self):
        """Test reconnection resubscribes to channels."""
        config = ConnectionConfig(url="ws://localhost:8000")
        stream = WebSocketStream(config)
        mock_websocket = AsyncMock()
        
        async def mock_connect_coro(*args, **kwargs):
            return mock_websocket
        
        with patch('stockiq.data.streams.websocket.websockets.connect', side_effect=mock_connect_coro):
            # Initial connection and subscription
            await stream.connect()
            await stream.subscribe(["AAPL", "TSLA"])
            
            # Simulate reconnection
            stream.websocket = None
            stream.status = StreamStatus.DISCONNECTED
            await stream.connect()
            
            # Should resubscribe to both channels
            assert stream.websocket.send.call_count >= 2


class TestRequirement12_1:
    """Test Requirement 12.1: Sub-500ms latency."""
    
    @pytest.mark.asyncio
    async def test_latency_target_configured(self):
        """Test latency target is 500ms as per requirement."""
        config = ConnectionConfig(url="ws://localhost:8000")
        assert config.latency_target_ms == 500
    
    @pytest.mark.asyncio
    async def test_latency_tracking_enabled(self):
        """Test latency tracking is active."""
        stream = WebSocketStream(ConnectionConfig(url="ws://localhost:8000"))
        
        # Simulate fast message (under target)
        past_time = datetime.utcnow() - timedelta(milliseconds=200)
        message = {
            "channel": "AAPL",
            "timestamp": past_time.isoformat()
        }
        
        await stream.handle_message(message)
        
        metrics = stream.get_latency_metrics()
        assert metrics['message_count'] == 1
        assert metrics['avg_latency_ms'] < 500
        assert metrics['over_target_count'] == 0
    
    @pytest.mark.asyncio
    async def test_over_target_latency_detected(self):
        """Test detection of messages exceeding latency target."""
        stream = WebSocketStream(ConnectionConfig(url="ws://localhost:8000"))
        
        # Simulate slow message (over target)
        past_time = datetime.utcnow() - timedelta(milliseconds=700)
        message = {
            "channel": "AAPL",
            "timestamp": past_time.isoformat()
        }
        
        await stream.handle_message(message)
        
        metrics = stream.get_latency_metrics()
        assert metrics['over_target_count'] == 1
        assert metrics['success_rate'] < 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
