"""
Example usage of WebSocket streaming for real-time market data.

This example demonstrates:
- Connecting to a WebSocket stream
- Subscribing to multiple tickers
- Handling real-time price updates
- Monitoring latency metrics
- Graceful shutdown
"""

import asyncio
import signal
from datetime import datetime
from stockiq.data.streams.websocket import WebSocketStream, ConnectionConfig


async def main():
    """Main example function."""
    
    # Configure WebSocket connection
    # NOTE: Replace with your actual WebSocket URL and authentication
    config = ConnectionConfig(
        url="wss://stream.example.com/market-data",  # Example URL
        auth={
            "action": "auth",
            "key": "your_api_key_here"
        },
        latency_target_ms=500,  # 500ms latency target (Requirement 12.1)
        max_reconnect_attempts=5,
        reconnect_delay=1.0
    )
    
    # Create WebSocket stream
    stream = WebSocketStream(config)
    
    # Track received messages
    message_count = 0
    
    async def handle_price_update(data: dict):
        """Handle incoming price updates."""
        nonlocal message_count
        message_count += 1
        
        # Extract price data
        ticker = data.get('symbol') or data.get('channel')
        price = data.get('price')
        timestamp = data.get('timestamp')
        
        print(f"[{message_count}] {ticker}: ${price} @ {timestamp}")
    
    # Connect to WebSocket
    print("Connecting to WebSocket stream...")
    await stream.connect()
    print(f"Connected! Status: {stream.status}")
    
    # Subscribe to tickers
    tickers = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
    print(f"Subscribing to: {', '.join(tickers)}")
    await stream.subscribe(tickers, handle_price_update)
    print("Subscribed!")
    
    # Setup graceful shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler():
        """Handle shutdown signals."""
        print("\nReceived shutdown signal, closing stream...")
        shutdown_event.set()
    
    # Register signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    print("\n=== Streaming real-time market data ===")
    print("Press Ctrl+C to stop\n")
    
    # Run for a limited time (30 seconds) or until shutdown
    try:
        # Create tasks for message loop and metrics reporting
        message_task = asyncio.create_task(stream.run())
        
        # Periodic metrics reporting
        async def report_metrics():
            while not shutdown_event.is_set():
                await asyncio.sleep(10)
                metrics = stream.get_latency_metrics()
                print(f"\n--- Latency Metrics ---")
                print(f"Messages: {metrics['message_count']}")
                print(f"Avg Latency: {metrics['avg_latency_ms']:.2f}ms")
                print(f"Min Latency: {metrics['min_latency_ms']:.2f}ms")
                print(f"Max Latency: {metrics['max_latency_ms']:.2f}ms")
                print(f"Success Rate: {metrics['success_rate']:.1f}%")
                print(f"Over Target: {metrics['over_target_count']}\n")
        
        metrics_task = asyncio.create_task(report_metrics())
        
        # Wait for shutdown or 30 second timeout
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            print("\n30 second demo completed")
        
        # Cancel tasks
        message_task.cancel()
        metrics_task.cancel()
        
    finally:
        # Close stream
        print("\nClosing WebSocket stream...")
        await stream.close()
        
        # Final metrics
        metrics = stream.get_latency_metrics()
        print(f"\n=== Final Statistics ===")
        print(f"Total Messages: {message_count}")
        print(f"Average Latency: {metrics['avg_latency_ms']:.2f}ms")
        print(f"Success Rate: {metrics['success_rate']:.1f}%")
        print(f"Connection Status: {stream.status}")
        print("\nStream closed successfully!")


async def simple_example():
    """Simple example with minimal configuration."""
    
    # Simple configuration
    config = ConnectionConfig(url="wss://stream.example.com")
    stream = WebSocketStream(config)
    
    # Simple callback
    def on_message(data):
        print(f"Received: {data}")
    
    # Connect, subscribe, and run
    await stream.connect()
    await stream.subscribe(["AAPL"], on_message)
    
    # Run for 10 seconds
    try:
        await asyncio.wait_for(stream.run(), timeout=10.0)
    except asyncio.TimeoutError:
        pass
    
    # Close
    await stream.close()


async def multiple_callbacks_example():
    """Example with multiple callbacks for the same channel."""
    
    config = ConnectionConfig(url="wss://stream.example.com")
    stream = WebSocketStream(config)
    
    # Multiple callbacks for different purposes
    async def log_to_console(data):
        """Log to console."""
        print(f"Console: {data}")
    
    async def save_to_cache(data):
        """Save to Redis cache (placeholder)."""
        # In real implementation, would save to Redis
        pass
    
    async def update_database(data):
        """Save to database (placeholder)."""
        # In real implementation, would save to PostgreSQL
        pass
    
    await stream.connect()
    
    # Subscribe with first callback
    await stream.subscribe(["AAPL"], log_to_console)
    
    # Add more callbacks to same channel
    await stream.subscribe(["AAPL"], save_to_cache)
    await stream.subscribe(["AAPL"], update_database)
    
    # All three callbacks will be invoked for AAPL messages
    try:
        await asyncio.wait_for(stream.run(), timeout=10.0)
    except asyncio.TimeoutError:
        pass
    
    await stream.close()


if __name__ == "__main__":
    # Run the main example
    print("=" * 60)
    print("WebSocket Streaming Example")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExample interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nExample completed!")
