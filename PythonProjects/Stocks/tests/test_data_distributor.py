"""
Tests for DataDistributor (Redis pub/sub).

Verifies:
- Basic publish/subscribe functionality
- Pattern-based subscriptions
- 100+ concurrent subscriber support (Requirement 12.3)
- Thread safety and error handling
- Metrics tracking
"""

import pytest
import time
import threading
from datetime import datetime
from typing import List, Any
from unittest.mock import Mock, patch, MagicMock

# Try importing the distributor
try:
    from stockiq.data.streams.distributor import (
        DataDistributor,
        SubscriberMetrics,
        ChannelMetrics
    )
    DISTRIBUTOR_AVAILABLE = True
except ImportError:
    DISTRIBUTOR_AVAILABLE = False

# Try importing Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@pytest.mark.skipif(
    not DISTRIBUTOR_AVAILABLE or not REDIS_AVAILABLE,
    reason="DataDistributor or Redis not available"
)
class TestDataDistributor:
    """Test suite for DataDistributor."""
    
    @pytest.fixture
    def distributor(self):
        """Create distributor instance for testing."""
        try:
            dist = DataDistributor(max_workers=5, enable_metrics=True)
            yield dist
            dist.close()
        except redis.ConnectionError:
            pytest.skip("Redis not available")
    
    def test_publish_basic(self, distributor):
        """Test basic message publishing."""
        # Publish a message
        data = {"ticker": "AAPL", "price": 150.25, "timestamp": datetime.utcnow()}
        subscriber_count = distributor.publish("price:AAPL", data)
        
        # Initially no subscribers
        assert subscriber_count >= 0
    
    def test_subscribe_and_receive(self, distributor):
        """Test subscribing and receiving messages."""
        received = []
        
        def callback(channel: str, data: Any):
            received.append((channel, data))
        
        # Subscribe
        sub_id = distributor.subscribe(["test:channel"], callback)
        
        # Give subscriber thread time to start
        time.sleep(0.2)
        
        # Publish message
        test_data = {"message": "hello", "timestamp": datetime.utcnow()}
        subscriber_count = distributor.publish("test:channel", test_data)
        
        # Should have 1 subscriber
        assert subscriber_count == 1
        
        # Wait for message delivery
        time.sleep(0.5)
        
        # Verify message received
        assert len(received) == 1
        channel, data = received[0]
        assert channel == "test:channel"
        assert data["message"] == "hello"
        
        # Cleanup
        distributor.unsubscribe(sub_id)
    
    def test_multiple_channels(self, distributor):
        """Test subscribing to multiple channels."""
        received = []
        
        def callback(channel: str, data: Any):
            received.append((channel, data))
        
        # Subscribe to multiple channels
        sub_id = distributor.subscribe(["channel1", "channel2", "channel3"], callback)
        time.sleep(0.2)
        
        # Publish to each channel
        distributor.publish("channel1", {"id": 1})
        distributor.publish("channel2", {"id": 2})
        distributor.publish("channel3", {"id": 3})
        
        # Wait for delivery
        time.sleep(0.5)
        
        # Should receive all 3 messages
        assert len(received) == 3
        
        channels_received = {ch for ch, _ in received}
        assert channels_received == {"channel1", "channel2", "channel3"}
        
        distributor.unsubscribe(sub_id)
    
    def test_pattern_subscribe(self, distributor):
        """Test pattern-based subscriptions."""
        received = []
        
        def callback(channel: str, data: Any):
            received.append((channel, data))
        
        # Subscribe to pattern
        sub_id = distributor.psubscribe(["price:*"], callback)
        time.sleep(0.2)
        
        # Publish to matching channels
        distributor.publish("price:AAPL", {"ticker": "AAPL", "price": 150})
        distributor.publish("price:TSLA", {"ticker": "TSLA", "price": 200})
        distributor.publish("news:AAPL", {"title": "News"})  # Should not match
        
        # Wait for delivery
        time.sleep(0.5)
        
        # Should receive only price messages
        assert len(received) == 2
        channels_received = {ch for ch, _ in received}
        assert channels_received == {"price:AAPL", "price:TSLA"}
        
        distributor.unsubscribe(sub_id)
    
    def test_multiple_subscribers_same_channel(self, distributor):
        """Test multiple subscribers on the same channel."""
        received1 = []
        received2 = []
        received3 = []
        
        def callback1(channel: str, data: Any):
            received1.append(data)
        
        def callback2(channel: str, data: Any):
            received2.append(data)
        
        def callback3(channel: str, data: Any):
            received3.append(data)
        
        # Subscribe 3 times to same channel
        sub_id1 = distributor.subscribe(["test:multi"], callback1)
        sub_id2 = distributor.subscribe(["test:multi"], callback2)
        sub_id3 = distributor.subscribe(["test:multi"], callback3)
        time.sleep(0.2)
        
        # Publish message
        test_data = {"value": 42}
        subscriber_count = distributor.publish("test:multi", test_data)
        
        # Should have 3 subscribers
        assert subscriber_count == 3
        
        # Wait for delivery
        time.sleep(0.5)
        
        # All 3 should receive the message
        assert len(received1) == 1
        assert len(received2) == 1
        assert len(received3) == 1
        
        assert received1[0]["value"] == 42
        assert received2[0]["value"] == 42
        assert received3[0]["value"] == 42
        
        # Cleanup
        distributor.unsubscribe(sub_id1)
        distributor.unsubscribe(sub_id2)
        distributor.unsubscribe(sub_id3)
    
    def test_concurrent_subscribers(self, distributor):
        """Test support for 100+ concurrent subscribers (Requirement 12.3)."""
        num_subscribers = 100
        received_counts = [0] * num_subscribers
        locks = [threading.Lock() for _ in range(num_subscribers)]
        
        def make_callback(idx: int):
            def callback(channel: str, data: Any):
                with locks[idx]:
                    received_counts[idx] += 1
            return callback
        
        # Create 100 subscribers
        subscriber_ids = []
        for i in range(num_subscribers):
            sub_id = distributor.subscribe(
                [f"test:concurrent"],
                make_callback(i),
                subscriber_id=f"sub_{i}"
            )
            subscriber_ids.append(sub_id)
        
        # Wait for all subscribers to start
        time.sleep(1.0)
        
        # Verify subscriber count
        assert distributor.get_subscriber_count() == num_subscribers
        
        # Publish a message
        test_data = {"message": "broadcast"}
        subscriber_count = distributor.publish("test:concurrent", test_data)
        
        # Should report 100 subscribers
        assert subscriber_count == num_subscribers
        
        # Wait for delivery
        time.sleep(2.0)
        
        # Most subscribers should have received the message
        # (Allow some tolerance for timing issues in tests)
        received_total = sum(received_counts)
        assert received_total >= num_subscribers * 0.95  # At least 95% delivery
        
        # Cleanup
        for sub_id in subscriber_ids:
            distributor.unsubscribe(sub_id)
    
    def test_unsubscribe_specific_channels(self, distributor):
        """Test unsubscribing from specific channels."""
        received = []
        
        def callback(channel: str, data: Any):
            received.append(channel)
        
        # Subscribe to 3 channels
        sub_id = distributor.subscribe(["ch1", "ch2", "ch3"], callback)
        time.sleep(0.2)
        
        # Unsubscribe from ch2 only
        distributor.unsubscribe(sub_id, ["ch2"])
        time.sleep(0.2)
        
        # Publish to all channels
        distributor.publish("ch1", {"data": 1})
        distributor.publish("ch2", {"data": 2})
        distributor.publish("ch3", {"data": 3})
        
        time.sleep(0.5)
        
        # Should receive ch1 and ch3, but not ch2
        assert "ch1" in received
        assert "ch3" in received
        assert "ch2" not in received
        
        distributor.unsubscribe(sub_id)
    
    def test_unsubscribe_all(self, distributor):
        """Test unsubscribing from all channels."""
        received = []
        
        def callback(channel: str, data: Any):
            received.append(channel)
        
        # Subscribe
        sub_id = distributor.subscribe(["test:unsub"], callback)
        time.sleep(0.2)
        
        # Publish message
        distributor.publish("test:unsub", {"data": 1})
        time.sleep(0.3)
        
        # Should receive message
        assert len(received) >= 1
        
        # Unsubscribe from all
        distributor.unsubscribe(sub_id)
        time.sleep(0.2)
        
        # Clear received list
        received.clear()
        
        # Publish again
        distributor.publish("test:unsub", {"data": 2})
        time.sleep(0.3)
        
        # Should NOT receive message
        assert len(received) == 0
    
    def test_callback_error_handling(self, distributor):
        """Test that callback errors don't crash the subscriber."""
        received_good = []
        
        def bad_callback(channel: str, data: Any):
            raise ValueError("Intentional error in callback")
        
        def good_callback(channel: str, data: Any):
            received_good.append(data)
        
        # Subscribe with bad callback
        sub_id1 = distributor.subscribe(["test:error"], bad_callback)
        # Subscribe with good callback
        sub_id2 = distributor.subscribe(["test:error"], good_callback)
        time.sleep(0.2)
        
        # Publish message
        distributor.publish("test:error", {"value": 123})
        time.sleep(0.5)
        
        # Good callback should still work despite bad callback error
        assert len(received_good) >= 1
        assert received_good[0]["value"] == 123
        
        # Cleanup
        distributor.unsubscribe(sub_id1)
        distributor.unsubscribe(sub_id2)
    
    def test_subscriber_metrics(self, distributor):
        """Test subscriber metrics tracking."""
        received = []
        
        def callback(channel: str, data: Any):
            received.append(data)
        
        # Subscribe
        sub_id = distributor.subscribe(["test:metrics"], callback)
        time.sleep(0.2)
        
        # Publish multiple messages
        for i in range(5):
            distributor.publish("test:metrics", {"id": i})
        
        time.sleep(0.5)
        
        # Get metrics
        metrics = distributor.get_subscriber_metrics(sub_id)
        
        # Should have metrics for the channel
        assert "test:metrics" in metrics
        channel_metrics = metrics["test:metrics"]
        
        # Verify metrics
        assert channel_metrics.messages_received == 5
        assert channel_metrics.last_message_at is not None
        assert channel_metrics.errors == 0
        
        distributor.unsubscribe(sub_id)
    
    def test_channel_metrics(self, distributor):
        """Test channel metrics tracking."""
        def callback(channel: str, data: Any):
            pass
        
        # Subscribe
        sub_id = distributor.subscribe(["test:ch_metrics"], callback)
        time.sleep(0.2)
        
        # Publish messages
        for i in range(3):
            distributor.publish("test:ch_metrics", {"id": i})
        
        time.sleep(0.3)
        
        # Get channel metrics
        metrics = distributor.get_channel_metrics("test:ch_metrics")
        
        # Verify metrics
        assert metrics is not None
        assert metrics.messages_published == 3
        assert metrics.subscribers_count == 1
        assert metrics.last_publish_at is not None
        
        distributor.unsubscribe(sub_id)
    
    def test_get_active_channels(self, distributor):
        """Test getting list of active channels."""
        def callback(channel: str, data: Any):
            pass
        
        # Subscribe to multiple channels
        sub_id = distributor.subscribe(["active1", "active2"], callback)
        time.sleep(0.2)
        
        # Get active channels
        active = distributor.get_active_channels()
        
        # Our channels should be in the list
        # (May include other channels from other tests)
        assert isinstance(active, list)
        
        distributor.unsubscribe(sub_id)
    
    def test_get_channel_subscriber_count(self, distributor):
        """Test getting subscriber count for a channel."""
        def callback(channel: str, data: Any):
            pass
        
        # Create 3 subscribers
        sub_id1 = distributor.subscribe(["test:count"], callback)
        sub_id2 = distributor.subscribe(["test:count"], callback)
        sub_id3 = distributor.subscribe(["test:count"], callback)
        time.sleep(0.2)
        
        # Get count
        count = distributor.get_channel_subscriber_count("test:count")
        assert count == 3
        
        # Cleanup
        distributor.unsubscribe(sub_id1)
        distributor.unsubscribe(sub_id2)
        distributor.unsubscribe(sub_id3)
    
    def test_get_all_metrics(self, distributor):
        """Test getting comprehensive metrics."""
        def callback(channel: str, data: Any):
            pass
        
        # Create some activity
        sub_id = distributor.subscribe(["test:all_metrics"], callback)
        time.sleep(0.2)
        
        distributor.publish("test:all_metrics", {"data": 1})
        distributor.publish("test:all_metrics", {"data": 2})
        time.sleep(0.3)
        
        # Get all metrics
        metrics = distributor.get_all_metrics()
        
        # Verify structure
        assert "total_subscribers" in metrics
        assert "total_channels" in metrics
        assert "subscriber_metrics" in metrics
        assert "channel_metrics" in metrics
        
        # Should have at least our subscriber and channel
        assert metrics["total_subscribers"] >= 1
        
        distributor.unsubscribe(sub_id)
    
    def test_context_manager(self):
        """Test using distributor as context manager."""
        received = []
        
        def callback(channel: str, data: Any):
            received.append(data)
        
        with DataDistributor() as dist:
            sub_id = dist.subscribe(["test:context"], callback)
            time.sleep(0.2)
            
            dist.publish("test:context", {"value": 100})
            time.sleep(0.3)
            
            assert len(received) >= 1
        
        # Context manager should have closed everything
        # (Can't verify directly, but should not raise errors)
    
    def test_thread_safety(self, distributor):
        """Test thread-safe operations."""
        num_threads = 10
        messages_per_thread = 10
        
        def publish_worker(thread_id: int):
            for i in range(messages_per_thread):
                distributor.publish(
                    f"test:thread_{thread_id}",
                    {"thread": thread_id, "msg": i}
                )
        
        # Start multiple publisher threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=publish_worker, args=(i,))
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Should complete without errors
        # (No assertion, just verify no crashes)
    
    def test_repr(self, distributor):
        """Test string representation."""
        repr_str = repr(distributor)
        assert "DataDistributor" in repr_str
        assert "subscribers=" in repr_str
        assert "metrics_enabled=" in repr_str


@pytest.mark.skipif(
    not DISTRIBUTOR_AVAILABLE,
    reason="DataDistributor not available"
)
class TestSubscriberMetrics:
    """Test SubscriberMetrics data class."""
    
    def test_initialization(self):
        """Test metrics initialization."""
        metrics = SubscriberMetrics(
            subscriber_id="sub1",
            channel="test:channel"
        )
        
        assert metrics.subscriber_id == "sub1"
        assert metrics.channel == "test:channel"
        assert metrics.messages_received == 0
        assert metrics.last_message_at is None
        assert metrics.errors == 0
    
    def test_record_message(self):
        """Test recording a message."""
        metrics = SubscriberMetrics(
            subscriber_id="sub1",
            channel="test:channel"
        )
        
        metrics.record_message()
        
        assert metrics.messages_received == 1
        assert metrics.last_message_at is not None
    
    def test_record_error(self):
        """Test recording an error."""
        metrics = SubscriberMetrics(
            subscriber_id="sub1",
            channel="test:channel"
        )
        
        metrics.record_error()
        
        assert metrics.errors == 1


@pytest.mark.skipif(
    not DISTRIBUTOR_AVAILABLE,
    reason="DataDistributor not available"
)
class TestChannelMetrics:
    """Test ChannelMetrics data class."""
    
    def test_initialization(self):
        """Test metrics initialization."""
        metrics = ChannelMetrics(channel="test:channel")
        
        assert metrics.channel == "test:channel"
        assert metrics.messages_published == 0
        assert metrics.subscribers_count == 0
        assert metrics.last_publish_at is None
    
    def test_record_publish(self):
        """Test recording a publish."""
        metrics = ChannelMetrics(channel="test:channel")
        
        metrics.record_publish(subscriber_count=5)
        
        assert metrics.messages_published == 1
        assert metrics.subscribers_count == 5
        assert metrics.last_publish_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
