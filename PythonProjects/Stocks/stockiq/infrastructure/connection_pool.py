"""
Connection pooling and automatic reconnection with exponential backoff.

This module provides enhanced connection management for database and external
services with automatic reconnection and exponential backoff strategies.

Features:
- Exponential backoff for failed connections
- Automatic reconnection on connection loss
- Connection health checks
- Detailed connection metrics
"""

import time
from typing import Optional, Callable, Any
from contextlib import contextmanager
import random
import structlog
from sqlalchemy.exc import OperationalError, DBAPIError
from sqlalchemy.orm import Session

from .database import get_db_context, get_engine
from .cache import get_cache

logger = structlog.get_logger(__name__)


class ExponentialBackoff:
    """
    Exponential backoff strategy for retrying failed operations.
    
    Implements exponential backoff with jitter to avoid thundering herd:
    wait_time = min(base * (2 ** attempt) + jitter, max_wait)
    """
    
    def __init__(
        self,
        base_delay: float = 0.5,
        max_delay: float = 60.0,
        max_attempts: int = 5,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Initialize exponential backoff strategy.
        
        Args:
            base_delay: Base delay in seconds (default: 0.5)
            max_delay: Maximum delay in seconds (default: 60)
            max_attempts: Maximum number of attempts (default: 5)
            exponential_base: Base for exponential calculation (default: 2.0)
            jitter: Add random jitter to avoid thundering herd (default: True)
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_attempts = max_attempts
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.attempt = 0
    
    def get_delay(self) -> float:
        """
        Calculate delay for current attempt.
        
        Returns:
            Delay in seconds
        """
        if self.attempt >= self.max_attempts:
            return self.max_delay
        
        # Calculate exponential delay
        delay = self.base_delay * (self.exponential_base ** self.attempt)
        
        # Add jitter (±25% of delay)
        if self.jitter:
            jitter_amount = delay * 0.25
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        # Cap at max_delay
        delay = min(delay, self.max_delay)
        
        return max(0, delay)
    
    def sleep(self) -> bool:
        """
        Sleep for the calculated delay and increment attempt counter.
        
        Returns:
            True if should continue retrying, False if max attempts reached
        """
        if self.attempt >= self.max_attempts:
            logger.warning(
                "exponential_backoff_max_attempts",
                attempts=self.attempt,
                max_attempts=self.max_attempts
            )
            return False
        
        delay = self.get_delay()
        
        logger.info(
            "exponential_backoff_sleeping",
            attempt=self.attempt + 1,
            max_attempts=self.max_attempts,
            delay=delay
        )
        
        time.sleep(delay)
        self.attempt += 1
        
        return True
    
    def reset(self):
        """Reset attempt counter."""
        self.attempt = 0


class DatabaseConnectionManager:
    """
    Manages database connections with automatic reconnection.
    
    Provides connection pooling through SQLAlchemy with automatic
    reconnection on connection failures using exponential backoff.
    """
    
    def __init__(self):
        """Initialize database connection manager."""
        self.engine = get_engine()
        self._connection_attempts = 0
        self._last_connection_error = None
        
        logger.info("database_connection_manager_initialized")
    
    @contextmanager
    def get_session_with_retry(self, max_retries: int = 3):
        """
        Get database session with automatic retry on connection failures.
        
        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            
        Yields:
            SQLAlchemy Session
            
        Raises:
            OperationalError: If all retry attempts fail
        """
        backoff = ExponentialBackoff(
            base_delay=0.5,
            max_delay=30.0,
            max_attempts=max_retries
        )
        
        last_error = None
        
        while True:
            try:
                with get_db_context() as session:
                    # Test connection
                    session.execute("SELECT 1")
                    
                    # Reset backoff on successful connection
                    backoff.reset()
                    self._connection_attempts = 0
                    
                    yield session
                    return
                    
            except (OperationalError, DBAPIError) as e:
                last_error = e
                self._connection_attempts += 1
                self._last_connection_error = str(e)
                
                logger.error(
                    "database_connection_failed",
                    attempt=self._connection_attempts,
                    error=str(e)
                )
                
                # Check if we should retry
                if not backoff.sleep():
                    logger.error(
                        "database_connection_max_retries",
                        attempts=self._connection_attempts,
                        last_error=str(last_error)
                    )
                    raise
                
                # Dispose of old connections and create new engine
                self.engine.dispose()
                self.engine = get_engine()
    
    def test_connection(self) -> bool:
        """
        Test database connection health.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            with get_db_context() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False
    
    def get_pool_status(self) -> dict:
        """
        Get connection pool status.
        
        Returns:
            Dictionary with pool statistics
        """
        pool = self.engine.pool
        
        return {
            'size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'connection_attempts': self._connection_attempts,
            'last_error': self._last_connection_error
        }


class CacheConnectionManager:
    """
    Manages Redis cache connections with automatic reconnection.
    
    Provides connection management for Redis with automatic
    reconnection on connection failures using exponential backoff.
    """
    
    def __init__(self):
        """Initialize cache connection manager."""
        self._connection_attempts = 0
        self._last_connection_error = None
        
        logger.info("cache_connection_manager_initialized")
    
    def execute_with_retry(
        self,
        operation: Callable[[], Any],
        max_retries: int = 3
    ) -> Optional[Any]:
        """
        Execute Redis operation with automatic retry.
        
        Args:
            operation: Callable that executes Redis operation
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            Operation result or None if all attempts fail
        """
        backoff = ExponentialBackoff(
            base_delay=0.1,
            max_delay=10.0,
            max_attempts=max_retries
        )
        
        last_error = None
        
        while True:
            try:
                result = operation()
                
                # Reset on successful operation
                backoff.reset()
                self._connection_attempts = 0
                
                return result
                
            except Exception as e:
                last_error = e
                self._connection_attempts += 1
                self._last_connection_error = str(e)
                
                logger.error(
                    "cache_operation_failed",
                    attempt=self._connection_attempts,
                    error=str(e)
                )
                
                # Check if we should retry
                if not backoff.sleep():
                    logger.error(
                        "cache_operation_max_retries",
                        attempts=self._connection_attempts,
                        last_error=str(last_error)
                    )
                    return None
    
    def test_connection(self) -> bool:
        """
        Test Redis connection health.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            cache = get_cache()
            cache.set("health_check", "ok", ttl=10)
            result = cache.get("health_check", deserialize=False)
            return result == "ok"
        except Exception as e:
            logger.error("cache_health_check_failed", error=str(e))
            return False


# Global connection managers
_db_connection_manager: Optional[DatabaseConnectionManager] = None
_cache_connection_manager: Optional[CacheConnectionManager] = None


def get_db_connection_manager() -> DatabaseConnectionManager:
    """Get or create the global database connection manager."""
    global _db_connection_manager
    
    if _db_connection_manager is None:
        _db_connection_manager = DatabaseConnectionManager()
    
    return _db_connection_manager


def get_cache_connection_manager() -> CacheConnectionManager:
    """Get or create the global cache connection manager."""
    global _cache_connection_manager
    
    if _cache_connection_manager is None:
        _cache_connection_manager = CacheConnectionManager()
    
    return _cache_connection_manager


@contextmanager
def db_session_with_retry(max_retries: int = 3):
    """
    Context manager for database session with automatic retry.
    
    Usage:
        with db_session_with_retry() as session:
            # Use session
            pass
    
    Args:
        max_retries: Maximum number of retry attempts
        
    Yields:
        SQLAlchemy Session
    """
    manager = get_db_connection_manager()
    with manager.get_session_with_retry(max_retries=max_retries) as session:
        yield session


def execute_cache_operation_with_retry(
    operation: Callable[[], Any],
    max_retries: int = 3
) -> Optional[Any]:
    """
    Execute cache operation with automatic retry.
    
    Usage:
        result = execute_cache_operation_with_retry(
            lambda: cache.get("key")
        )
    
    Args:
        operation: Callable that executes cache operation
        max_retries: Maximum number of retry attempts
        
    Returns:
        Operation result or None if all attempts fail
    """
    manager = get_cache_connection_manager()
    return manager.execute_with_retry(operation, max_retries=max_retries)
