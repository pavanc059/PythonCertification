"""
Redis pub/sub data distribution for real-time updates.

This module implements a high-performance data distribution system
using Redis pub/sub to broadcast real-time market data to multiple
subscribers with support for 100+ concurrent connections (Requirement 12.3).
"""

import asyncio
import logging
import pickle
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

import structlog

from ...infrastructure.cache import get_redis_client

logger = structlog.get_logger(__name__)


@dataclass
class SubscriberMetrics:
    """Metrics for a subscriber."""
    subscriber_id: str
    channel: str
    messages_received: int = 0
    last_message_at: Optional[datetime] = None
    subscribed_at: datetime = field(default_factory=datetime.utcnow)
    errors: int = 0
    
    def record_message(self):
        """Record a successful message delivery."""
        self.messages_received += 1
        self.last_message_at = datetime.utcnow()
    
    def record_error(self):
        """Record a callback error."""
        self.errors += 1


@dataclass
class ChannelMetrics:
    """Metrics for a channel."""
    channel: str
    messages_published: int = 0
    subscribers_count: int = 0
    last_publish_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def record_publish(self, subscriber_count: int):
        """Record a message publish."""
        self.messages_published += 1
        self.subscribers_count = subscriber_count
        self.last_publish_at = datetime.utcnow()


class DataDistributor:
    """
    Redis pub/sub data distributor for real-time market data.
    
    This class provides a high-performance publish/subscribe system
    for distributing real-time data to multiple consumers. It supports:
    
    - Publishing data to named channels
    - Subscribing to channels with callback handlers
    - Pattern-based subscriptions (e.g., "price:*")
    - 100+ concurrent subscriber connections (Requirement 12.3)
    - Automatic serialization/deserialization
    - Connection pooling and thread safety
    - Subscriber metrics and monitoring
    
    The distributor uses Redis pub/sub as the underlying transport,
    which provides:
    - Fire-and-forget message delivery
    - No message persistence (real-time only)
    - Efficient broadcasting to N subscribers
    - Horizontal scalability
    
    Example:
        ```python
        distributor = DataDistributor()
        
        # Publisher
        price_data = {"ticker": "AAPL", "price": 150.25}
        distributor.publish("price:AAPL", price_data)
        
        # Subscriber
        def handle_price(channel: str, data: Any):
            print(f"Received on {channel}: {data}")
        
        distributor.subscribe(["price:AAPL", "price:TSLA"], handle_price)
        ```
    
    Threading Model:
        - Publisher calls are thread-safe and non-blocking
        - Each subscriber group runs in a dedicated background thread
        - Callbacks are executed in the subscriber thread
        - For async callbacks, use the async variant methods
    """
    
    def __init__(
        self,
        max_workers: int = 10,
        enable_metrics: bool = True
    ):
        """
        Initialize data distributor.
        
        Args:
            max_workers: Maximum worker threads for callback execution
            enable_metrics: Enable subscriber and channel metrics
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis library required for pub/sub distribution. "
                "Install with: pip install redis"
            )
        
        self.redis_client = get_redis_client()
        self.enable_metrics = enable_metrics
        
        # Thread pool for callback execution
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Subscriber management
        # Format: {subscriber_id: {pubsub_instance, thread, channels, callbacks}}
        self._subscribers: Dict[str, Dict[str, Any]] = {}
        self._subscriber_lock = threading.RLock()
        self._next_subscriber_id = 0
        
        # Metrics
        if self.enable_metrics:
            self._subscriber_metrics: Dict[str, SubscriberMetrics] = {}
            self._channel_metrics: Dict[str, ChannelMetrics] = {}
            self._metrics_lock = threading.RLock()
        
        # Graceful shutdown
        self._shutdown = threading.Event()
        
        logger.info(
            "data_distributor_initialized",
            max_workers=max_workers,
            metrics_enabled=enable_metrics
        )
    
    def publish(self, channel: str, data: Any) -> int:
        """
        Publish data to a Redis pub/sub channel.
        
        This is a non-blocking operation that serializes and publishes
        the data to all subscribers of the specified channel.
        
        Args:
            channel: Channel name (e.g., "price:AAPL", "news:latest")
            data: Data to publish (will be pickled for serialization)
        
        Returns:
            Number of subscribers that received the message
        
        Example:
            ```python
            # Publish price update
            price = {"ticker": "AAPL", "price": 150.25, "timestamp": datetime.utcnow()}
            subscriber_count = distributor.publish("price:AAPL", price)
            print(f"Delivered to {subscriber_count} subscribers")
            ```
        """
        try:
            # Serialize data
            serialized = pickle.dumps(data)
            
            # Publish to Redis channel
            subscriber_count = self.redis_client.publish(channel, serialized)
            
            # Update metrics
            if self.enable_metrics:
                self._update_channel_metrics(channel, subscriber_count)
            
            logger.debug(
                "pubsub_published",
                channel=channel,
                subscribers=subscriber_count,
                data_size=len(serialized)
            )
            
            return subscriber_count
            
        except Exception as e:
            logger.error(
                "pubsub_publish_failed",
                channel=channel,
                error=str(e),
                exc_info=True
            )
            return 0
    
    def subscribe(
        self,
        channels: List[str],
        callback: Callable[[str, Any], None],
        subscriber_id: Optional[str] = None
    ) -> str:
        """
        Subscribe to Redis pub/sub channels.
        
        This creates a background thread that listens for messages on the
        specified channels and invokes the callback when messages arrive.
        
        The callback is executed in a thread pool to prevent blocking
        the message receive loop, enabling support for 100+ concurrent
        subscribers (Requirement 12.3).
        
        Args:
            channels: List of channel names to subscribe to
            callback: Function called with (channel, data) when message received
            subscriber_id: Optional unique identifier for this subscriber.
                          If not provided, a unique ID is auto-generated.
        
        Returns:
            Subscriber ID (use for unsubscribe)
        
        Example:
            ```python
            def handle_price(channel: str, data: dict):
                ticker = data.get('ticker')
                price = data.get('price')
                print(f"{ticker}: ${price}")
            
            sub_id = distributor.subscribe(["price:AAPL", "price:TSLA"], handle_price)
            # Later...
            distributor.unsubscribe(sub_id)
            ```
        
        Note:
            - Callbacks should be fast (< 100ms) to avoid blocking
            - For long-running callbacks, spawn a separate task
            - Callbacks are NOT guaranteed to execute in order
            - If callback raises exception, it's logged but doesn't stop subscriber
        """
        if not channels:
            raise ValueError("Must provide at least one channel")
        
        with self._subscriber_lock:
            # Generate subscriber ID if not provided
            if subscriber_id is None:
                subscriber_id = f"subscriber_{self._next_subscriber_id}"
                self._next_subscriber_id += 1
            
            # Check if subscriber already exists
            if subscriber_id in self._subscribers:
                logger.warning(
                    "subscriber_already_exists",
                    subscriber_id=subscriber_id,
                    existing_channels=self._subscribers[subscriber_id]['channels']
                )
                # Add to existing subscription
                existing_pubsub = self._subscribers[subscriber_id]['pubsub']
                existing_pubsub.subscribe(*channels)
                self._subscribers[subscriber_id]['channels'].update(channels)
                self._subscribers[subscriber_id]['callbacks'][tuple(channels)] = callback
                return subscriber_id
            
            # Create new pub/sub instance
            pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(*channels)
            
            # Store subscriber info
            subscriber_info = {
                'pubsub': pubsub,
                'channels': set(channels),
                'callbacks': {tuple(channels): callback},
                'thread': None,
                'running': threading.Event()
            }
            
            self._subscribers[subscriber_id] = subscriber_info
            
            # Initialize metrics
            if self.enable_metrics:
                with self._metrics_lock:
                    for channel in channels:
                        metrics_key = f"{subscriber_id}:{channel}"
                        self._subscriber_metrics[metrics_key] = SubscriberMetrics(
                            subscriber_id=subscriber_id,
                            channel=channel
                        )
            
            # Start listener thread
            thread = threading.Thread(
                target=self._subscriber_loop,
                args=(subscriber_id, pubsub, callback),
                daemon=True,
                name=f"PubSubListener-{subscriber_id}"
            )
            thread.start()
            subscriber_info['thread'] = thread
            subscriber_info['running'].set()
            
            logger.info(
                "pubsub_subscribed",
                subscriber_id=subscriber_id,
                channels=channels
            )
            
            return subscriber_id
    
    def _subscriber_loop(
        self,
        subscriber_id: str,
        pubsub: Any,
        callback: Callable[[str, Any], None]
    ):
        """
        Background thread that listens for pub/sub messages.
        
        This loop runs continuously until unsubscribe() is called.
        Messages are dispatched to the callback via the thread pool.
        """
        logger.info("subscriber_loop_started", subscriber_id=subscriber_id)
        
        try:
            while not self._shutdown.is_set():
                # Check if this subscriber is still active
                with self._subscriber_lock:
                    if subscriber_id not in self._subscribers:
                        break
                    if not self._subscribers[subscriber_id]['running'].is_set():
                        break
                
                try:
                    # Get message with timeout (non-blocking)
                    message = pubsub.get_message(timeout=1.0)
                    
                    if message and message['type'] == 'message':
                        # Deserialize data
                        channel = message['channel'].decode('utf-8')
                        data = pickle.loads(message['data'])
                        
                        # Execute callback in thread pool
                        self.executor.submit(
                            self._execute_callback,
                            subscriber_id,
                            channel,
                            data,
                            callback
                        )
                        
                except Exception as e:
                    logger.error(
                        "subscriber_message_error",
                        subscriber_id=subscriber_id,
                        error=str(e)
                    )
                    
        except Exception as e:
            logger.error(
                "subscriber_loop_failed",
                subscriber_id=subscriber_id,
                error=str(e),
                exc_info=True
            )
        finally:
            logger.info("subscriber_loop_stopped", subscriber_id=subscriber_id)
    
    def _execute_callback(
        self,
        subscriber_id: str,
        channel: str,
        data: Any,
        callback: Callable[[str, Any], None]
    ):
        """Execute callback with error handling and metrics."""
        try:
            # Invoke callback
            callback(channel, data)
            
            # Update metrics
            if self.enable_metrics:
                with self._metrics_lock:
                    metrics_key = f"{subscriber_id}:{channel}"
                    if metrics_key in self._subscriber_metrics:
                        self._subscriber_metrics[metrics_key].record_message()
            
            logger.debug(
                "callback_executed",
                subscriber_id=subscriber_id,
                channel=channel
            )
            
        except Exception as e:
            logger.error(
                "callback_error",
                subscriber_id=subscriber_id,
                channel=channel,
                error=str(e),
                exc_info=True
            )
            
            # Update error metrics
            if self.enable_metrics:
                with self._metrics_lock:
                    metrics_key = f"{subscriber_id}:{channel}"
                    if metrics_key in self._subscriber_metrics:
                        self._subscriber_metrics[metrics_key].record_error()
    
    def unsubscribe(self, subscriber_id: str, channels: Optional[List[str]] = None):
        """
        Unsubscribe from channels or remove subscriber entirely.
        
        Args:
            subscriber_id: Subscriber ID returned from subscribe()
            channels: Optional list of specific channels to unsubscribe from.
                     If None, unsubscribes from all channels and removes subscriber.
        
        Example:
            ```python
            # Unsubscribe from specific channels
            distributor.unsubscribe(sub_id, ["price:AAPL"])
            
            # Unsubscribe from all channels and cleanup
            distributor.unsubscribe(sub_id)
            ```
        """
        with self._subscriber_lock:
            if subscriber_id not in self._subscribers:
                logger.warning(
                    "subscriber_not_found",
                    subscriber_id=subscriber_id
                )
                return
            
            subscriber_info = self._subscribers[subscriber_id]
            pubsub = subscriber_info['pubsub']
            
            if channels is None:
                # Unsubscribe from all channels and cleanup
                try:
                    pubsub.unsubscribe()
                    pubsub.close()
                except Exception as e:
                    logger.error(
                        "pubsub_unsubscribe_error",
                        subscriber_id=subscriber_id,
                        error=str(e)
                    )
                
                # Stop the listener thread
                subscriber_info['running'].clear()
                thread = subscriber_info['thread']
                if thread and thread.is_alive():
                    thread.join(timeout=5.0)
                
                # Remove from registry
                del self._subscribers[subscriber_id]
                
                # Clean up metrics
                if self.enable_metrics:
                    with self._metrics_lock:
                        keys_to_remove = [
                            k for k in self._subscriber_metrics.keys()
                            if k.startswith(f"{subscriber_id}:")
                        ]
                        for key in keys_to_remove:
                            del self._subscriber_metrics[key]
                
                logger.info(
                    "subscriber_removed",
                    subscriber_id=subscriber_id
                )
            else:
                # Unsubscribe from specific channels
                try:
                    pubsub.unsubscribe(*channels)
                    subscriber_info['channels'].difference_update(channels)
                    
                    # Clean up metrics for these channels
                    if self.enable_metrics:
                        with self._metrics_lock:
                            for channel in channels:
                                metrics_key = f"{subscriber_id}:{channel}"
                                if metrics_key in self._subscriber_metrics:
                                    del self._subscriber_metrics[metrics_key]
                    
                    logger.info(
                        "channels_unsubscribed",
                        subscriber_id=subscriber_id,
                        channels=channels
                    )
                    
                    # If no channels remain, remove subscriber
                    if not subscriber_info['channels']:
                        self.unsubscribe(subscriber_id)
                        
                except Exception as e:
                    logger.error(
                        "pubsub_unsubscribe_error",
                        subscriber_id=subscriber_id,
                        channels=channels,
                        error=str(e)
                    )
    
    def psubscribe(
        self,
        patterns: List[str],
        callback: Callable[[str, Any], None],
        subscriber_id: Optional[str] = None
    ) -> str:
        """
        Subscribe to channels using patterns (pattern subscribe).
        
        Supports wildcards: '*' matches any characters within a segment,
        '?' matches exactly one character.
        
        Args:
            patterns: List of channel patterns (e.g., ["price:*", "news:ticker:?"])
            callback: Function called with (channel, data) when message received
            subscriber_id: Optional unique identifier for this subscriber
        
        Returns:
            Subscriber ID
        
        Example:
            ```python
            def handle_all_prices(channel: str, data: dict):
                ticker = channel.split(':')[1]
                print(f"Price update for {ticker}: {data}")
            
            # Subscribe to all price channels
            sub_id = distributor.psubscribe(["price:*"], handle_all_prices)
            ```
        """
        if not patterns:
            raise ValueError("Must provide at least one pattern")
        
        with self._subscriber_lock:
            # Generate subscriber ID if not provided
            if subscriber_id is None:
                subscriber_id = f"psubscriber_{self._next_subscriber_id}"
                self._next_subscriber_id += 1
            
            # Create new pub/sub instance
            pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)
            pubsub.psubscribe(*patterns)
            
            # Store subscriber info
            subscriber_info = {
                'pubsub': pubsub,
                'channels': set(patterns),  # Store patterns
                'callbacks': {tuple(patterns): callback},
                'thread': None,
                'running': threading.Event(),
                'is_pattern': True
            }
            
            self._subscribers[subscriber_id] = subscriber_info
            
            # Start listener thread (pattern version)
            thread = threading.Thread(
                target=self._pattern_subscriber_loop,
                args=(subscriber_id, pubsub, callback),
                daemon=True,
                name=f"PubSubPatternListener-{subscriber_id}"
            )
            thread.start()
            subscriber_info['thread'] = thread
            subscriber_info['running'].set()
            
            logger.info(
                "pubsub_psubscribed",
                subscriber_id=subscriber_id,
                patterns=patterns
            )
            
            return subscriber_id
    
    def _pattern_subscriber_loop(
        self,
        subscriber_id: str,
        pubsub: Any,
        callback: Callable[[str, Any], None]
    ):
        """Background thread for pattern subscriptions."""
        logger.info("pattern_subscriber_loop_started", subscriber_id=subscriber_id)
        
        try:
            while not self._shutdown.is_set():
                # Check if this subscriber is still active
                with self._subscriber_lock:
                    if subscriber_id not in self._subscribers:
                        break
                    if not self._subscribers[subscriber_id]['running'].is_set():
                        break
                
                try:
                    # Get message with timeout
                    message = pubsub.get_message(timeout=1.0)
                    
                    if message and message['type'] == 'pmessage':
                        # Deserialize data
                        channel = message['channel'].decode('utf-8')
                        data = pickle.loads(message['data'])
                        
                        # Execute callback in thread pool
                        self.executor.submit(
                            self._execute_callback,
                            subscriber_id,
                            channel,
                            data,
                            callback
                        )
                        
                except Exception as e:
                    logger.error(
                        "pattern_subscriber_message_error",
                        subscriber_id=subscriber_id,
                        error=str(e)
                    )
                    
        except Exception as e:
            logger.error(
                "pattern_subscriber_loop_failed",
                subscriber_id=subscriber_id,
                error=str(e),
                exc_info=True
            )
        finally:
            logger.info("pattern_subscriber_loop_stopped", subscriber_id=subscriber_id)
    
    def get_active_channels(self) -> List[str]:
        """
        Get list of all active pub/sub channels.
        
        Returns:
            List of channel names with active subscribers
        """
        try:
            channels = self.redis_client.pubsub_channels()
            return [ch.decode('utf-8') for ch in channels]
        except Exception as e:
            logger.error("get_active_channels_failed", error=str(e))
            return []
    
    def get_channel_subscriber_count(self, channel: str) -> int:
        """
        Get number of subscribers for a channel.
        
        Args:
            channel: Channel name
        
        Returns:
            Number of active subscribers
        """
        try:
            result = self.redis_client.pubsub_numsub(channel)
            # Result format: [channel_bytes, count]
            if len(result) >= 2:
                return result[1]
            return 0
        except Exception as e:
            logger.error(
                "get_channel_subscriber_count_failed",
                channel=channel,
                error=str(e)
            )
            return 0
    
    def get_subscriber_count(self) -> int:
        """
        Get total number of active subscribers.
        
        Returns:
            Number of subscriber connections managed by this distributor
        """
        with self._subscriber_lock:
            return len(self._subscribers)
    
    def get_subscriber_metrics(self, subscriber_id: str) -> Dict[str, SubscriberMetrics]:
        """
        Get metrics for a specific subscriber.
        
        Args:
            subscriber_id: Subscriber ID
        
        Returns:
            Dictionary mapping channel to metrics
        """
        if not self.enable_metrics:
            return {}
        
        with self._metrics_lock:
            return {
                k.split(':', 1)[1]: v
                for k, v in self._subscriber_metrics.items()
                if k.startswith(f"{subscriber_id}:")
            }
    
    def get_channel_metrics(self, channel: str) -> Optional[ChannelMetrics]:
        """
        Get metrics for a specific channel.
        
        Args:
            channel: Channel name
        
        Returns:
            Channel metrics or None if not found
        """
        if not self.enable_metrics:
            return None
        
        with self._metrics_lock:
            return self._channel_metrics.get(channel)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics for all subscribers and channels.
        
        Returns:
            Dictionary with subscriber and channel metrics
        """
        if not self.enable_metrics:
            return {"metrics_disabled": True}
        
        with self._metrics_lock:
            return {
                'total_subscribers': len(set(
                    m.subscriber_id for m in self._subscriber_metrics.values()
                )),
                'total_channels': len(self._channel_metrics),
                'subscriber_metrics': {
                    k: {
                        'messages_received': v.messages_received,
                        'last_message_at': v.last_message_at.isoformat() if v.last_message_at else None,
                        'subscribed_at': v.subscribed_at.isoformat(),
                        'errors': v.errors
                    }
                    for k, v in self._subscriber_metrics.items()
                },
                'channel_metrics': {
                    k: {
                        'messages_published': v.messages_published,
                        'subscribers_count': v.subscribers_count,
                        'last_publish_at': v.last_publish_at.isoformat() if v.last_publish_at else None,
                        'created_at': v.created_at.isoformat()
                    }
                    for k, v in self._channel_metrics.items()
                }
            }
    
    def _update_channel_metrics(self, channel: str, subscriber_count: int):
        """Update metrics for a channel."""
        with self._metrics_lock:
            if channel not in self._channel_metrics:
                self._channel_metrics[channel] = ChannelMetrics(channel=channel)
            
            self._channel_metrics[channel].record_publish(subscriber_count)
    
    def close(self):
        """
        Gracefully shutdown the distributor.
        
        Unsubscribes all subscribers and closes connections.
        """
        logger.info("shutting_down_distributor")
        
        # Signal shutdown
        self._shutdown.set()
        
        # Unsubscribe all subscribers
        with self._subscriber_lock:
            subscriber_ids = list(self._subscribers.keys())
        
        for subscriber_id in subscriber_ids:
            try:
                self.unsubscribe(subscriber_id)
            except Exception as e:
                logger.error(
                    "unsubscribe_error_during_shutdown",
                    subscriber_id=subscriber_id,
                    error=str(e)
                )
        
        # Shutdown thread pool
        try:
            # Python 3.9+ supports timeout parameter
            self.executor.shutdown(wait=True)
        except TypeError:
            # Fall back for older Python versions
            self.executor.shutdown(wait=True)
        
        logger.info("distributor_shutdown_complete")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __repr__(self) -> str:
        return (
            f"DataDistributor("
            f"subscribers={self.get_subscriber_count()}, "
            f"metrics_enabled={self.enable_metrics})"
        )
