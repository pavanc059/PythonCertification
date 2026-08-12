# WebSocket Streaming Guide

## Overview

The WebSocket streaming module provides real-time market data with sub-500ms latency (Requirement 12.1). It supports automatic reconnection, multiple channel subscriptions, and comprehensive latency monitoring.

## Quick Start

```python
import asyncio
from stockiq.data.streams.websocket import WebSocketStream, ConnectionConfig

async def main():
    # Configure connection
    config = ConnectionConfig(
        url="wss://stream.example.com",
        latency_target_ms=500
    )
    
    # Create stream
    stream = WebSocketStream(config)
    
    # Define callback
    async def on_price_update(data):
        print(f"Price: {data}")
    
    # Connect and subscribe
    await stream.connect()
    await stream.subscribe(["AAPL", "TSLA"], on_price_update)
    
    # Run message loop
    await stream.run()

asyncio.run(main())
```

## Configuration

### ConnectionConfig

```python
config = ConnectionConfig(
    url="wss://stream.example.com",           # Required: WebSocket URL
    auth={"api_key": "your_key"},             # Optional: Authentication
    ping_interval=20,                          # Ping interval (seconds)
    ping_timeout=10,                           # Ping timeout (seconds)
    max_reconnect_attempts=5,                  # Max reconnection attempts
    reconnect_delay=1.0,                       # Initial reconnection delay
    max_reconnect_delay=60.0,                  # Max reconnection delay
    latency_target_ms=500                      # Latency target (Requirement 12.1)
)
```

## Core Features

### 1. Connection Management

```python
# Connect
await stream.connect()

# Check connection status
if stream.is_connected:
    print("Connected!")

# Connection will automatically reconnect on failure
# with exponential backoff: 1s → 2s → 4s → 8s → 16s → 32s → 60s (max)
```

### 2. Subscription Management

```python
# Subscribe to single ticker
await stream.subscribe(["AAPL"], callback)

# Subscribe to multiple tickers
await stream.subscribe(["AAPL", "TSLA", "MSFT"], callback)

# Unsubscribe
await stream.unsubscribe(["AAPL"])

# Subscriptions are automatically restored after reconnection
```

### 3. Message Handling

```python
# Synchronous callback
def sync_callback(data: dict):
    print(f"Received: {data}")

# Asynchronous callback
async def async_callback(data: dict):
    await save_to_database(data)
    print(f"Saved: {data}")

# Multiple callbacks for same channel
await stream.subscribe(["AAPL"], sync_callback)
await stream.subscribe(["AAPL"], async_callback)
```

### 4. Latency Monitoring

```python
# Get current metrics
metrics = stream.get_latency_metrics()

print(f"Messages: {metrics['message_count']}")
print(f"Avg Latency: {metrics['avg_latency_ms']:.2f}ms")
print(f"Min Latency: {metrics['min_latency_ms']:.2f}ms")
print(f"Max Latency: {metrics['max_latency_ms']:.2f}ms")
print(f"Success Rate: {metrics['success_rate']:.1f}%")
print(f"Over Target: {metrics['over_target_count']}")

# Latency is calculated from message timestamp
# Messages with latency > 500ms trigger warnings
```

### 5. Graceful Shutdown

```python
# Close connection (unsubscribes and cleans up)
await stream.close()

# Connection status will be StreamStatus.CLOSED
assert stream.status == StreamStatus.CLOSED
```

## Message Format

Expected message format from WebSocket server:

```json
{
    "channel": "AAPL",          // or "symbol": "AAPL"
    "price": 150.25,
    "volume": 1000000,
    "timestamp": "2025-01-23T10:30:00.123Z",  // ISO format, for latency calc
    "bid": 150.24,
    "ask": 150.26
}
```

## Error Handling

### Connection Errors

```python
try:
    await stream.connect()
except ConnectionError as e:
    # Raised after max_reconnect_attempts exceeded
    print(f"Failed to connect: {e}")
```

### Callback Errors

```python
# Callback errors are caught and logged, but don't crash the handler
def callback_with_error(data):
    raise ValueError("Something went wrong")
    # Error is logged, but other callbacks still execute

await stream.subscribe(["AAPL"], callback_with_error)
```

### Reconnection

Automatic reconnection occurs on:
- Connection timeout
- WebSocket closed unexpectedly
- Network errors

Subscriptions are preserved and resubscribed after reconnection.

## Connection States

```python
from stockiq.data.streams.websocket import StreamStatus

# Possible states:
StreamStatus.DISCONNECTED   # Initial state
StreamStatus.CONNECTING     # Connecting to server
StreamStatus.CONNECTED      # Connected and ready
StreamStatus.RECONNECTING   # Reconnecting after failure
StreamStatus.ERROR          # Max retries exceeded
StreamStatus.CLOSED         # Gracefully closed

# Check current status
print(stream.status)
```

## Advanced Usage

### Multiple Callbacks per Channel

```python
async def log_callback(data):
    print(f"Log: {data}")

async def cache_callback(data):
    await redis.set(f"price:{data['channel']}", data['price'])

async def db_callback(data):
    await db.insert('prices', data)

# All callbacks will be invoked for each message
await stream.subscribe(["AAPL"], log_callback)
await stream.subscribe(["AAPL"], cache_callback)
await stream.subscribe(["AAPL"], db_callback)
```

### Custom Message Loop

```python
# Run with timeout
try:
    await asyncio.wait_for(stream.run(), timeout=60.0)
except asyncio.TimeoutError:
    print("Stream stopped after 60 seconds")

# Or run with shutdown event
shutdown = asyncio.Event()

async def run_until_shutdown():
    task = asyncio.create_task(stream.run())
    await shutdown.wait()
    task.cancel()
    await stream.close()
```

### Authentication

```python
# API key authentication
config = ConnectionConfig(
    url="wss://stream.example.com",
    auth={"api_key": "your_api_key"}
)

# OAuth token authentication
config = ConnectionConfig(
    url="wss://stream.example.com",
    auth={
        "action": "authenticate",
        "token": "your_oauth_token"
    }
)

# Authentication message is sent automatically after connection
```

## Performance Characteristics

- **Latency Target**: 500ms (Requirement 12.1)
- **Reconnection**: Exponential backoff 1s → 60s max
- **Memory**: O(n) where n = number of subscriptions
- **Concurrency**: Supports multiple channel subscriptions per connection
- **Error Recovery**: Automatic reconnection with subscription preservation

## Integration Examples

### With Redis Pub/Sub

```python
import redis.asyncio as aioredis

redis_client = await aioredis.from_url("redis://localhost")

async def publish_to_redis(data):
    channel = f"price:{data['channel']}"
    await redis_client.publish(channel, json.dumps(data))

await stream.subscribe(["AAPL", "TSLA"], publish_to_redis)
```

### With Database Storage

```python
from sqlalchemy.ext.asyncio import AsyncSession

async def save_to_db(data):
    async with AsyncSession() as session:
        price = Price(
            ticker=data['channel'],
            price=data['price'],
            timestamp=data['timestamp']
        )
        session.add(price)
        await session.commit()

await stream.subscribe(["AAPL"], save_to_db)
```

### With Cache Update

```python
async def update_cache(data):
    key = f"price:{data['channel']}:latest"
    await redis.setex(key, 300, data['price'])  # 5 min TTL

await stream.subscribe(["AAPL"], update_cache)
```

## Troubleshooting

### High Latency

If latency consistently exceeds 500ms:

1. **Check Network**: Ping WebSocket server
2. **Check Load**: Reduce number of subscriptions
3. **Check Processing**: Ensure callbacks are fast
4. **Check Metrics**: Use `get_latency_metrics()` to identify patterns

### Connection Failures

If connections frequently fail:

1. **Check URL**: Verify WebSocket URL is correct
2. **Check Auth**: Verify authentication credentials
3. **Check Firewall**: Ensure WebSocket port is open
4. **Increase Retries**: Raise `max_reconnect_attempts`

### Missing Messages

If messages appear to be missing:

1. **Check Subscription**: Verify channel names
2. **Check Callback**: Ensure callback doesn't raise exceptions
3. **Check Logs**: Look for error messages
4. **Add Logging**: Log all received messages

## Dependencies

- **websockets** (>=12.0): WebSocket client library
- **Python** 3.8+ with asyncio support

Install with:
```bash
pip install websockets>=12.0
```

## See Also

- **Example Script**: `examples/websocket_stream_example.py`
- **Test Suite**: `tests/test_websocket_stream.py`
- **API Reference**: See docstrings in `stockiq/data/streams/websocket.py`
- **Requirements**: See Requirement 12.1, 12.2, 12.6 in `requirements.md`

## Support

For issues or questions:
1. Check test suite for usage examples
2. Review example scripts in `examples/`
3. Check debug logs (set log level to DEBUG)
4. Review connection metrics with `get_latency_metrics()`
