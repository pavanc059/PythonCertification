"""
Tests for connection pooling and exponential backoff.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.exc import OperationalError

from stockiq.infrastructure.connection_pool import (
    ExponentialBackoff,
    DatabaseConnectionManager,
    CacheConnectionManager,
    db_session_with_retry,
    execute_cache_operation_with_retry,
)


class TestExponentialBackoff:
    """Test ExponentialBackoff class."""
    
    def test_initialization(self):
        """Test exponential backoff initialization."""
        backoff = ExponentialBackoff(
            base_delay=0.5,
            max_delay=60.0,
            max_attempts=5
        )
        
        assert backoff.base_delay == 0.5
        assert backoff.max_delay == 60.0
        assert backoff.max_attempts == 5
        assert backoff.attempt == 0
    
    def test_get_delay_increases_exponentially(self):
        """Test that delay increases exponentially."""
        backoff = ExponentialBackoff(
            base_delay=1.0,
            max_delay=100.0,
            max_attempts=5,
            jitter=False  # Disable jitter for predictable testing
        )
        
        # First attempt: 1.0 * (2^0) = 1.0
        assert backoff.get_delay() == 1.0
        backoff.attempt = 1
        
        # Second attempt: 1.0 * (2^1) = 2.0
        assert backoff.get_delay() == 2.0
        backoff.attempt = 2
        
        # Third attempt: 1.0 * (2^2) = 4.0
        assert backoff.get_delay() == 4.0
        backoff.attempt = 3
        
        # Fourth attempt: 1.0 * (2^3) = 8.0
        assert backoff.get_delay() == 8.0
    
    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        backoff = ExponentialBackoff(
            base_delay=10.0,
            max_delay=30.0,
            max_attempts=10,
            jitter=False
        )
        
        backoff.attempt = 5  # Would be 10 * (2^5) = 320, but capped at 30
        assert backoff.get_delay() == 30.0
    
    def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness to delay."""
        backoff = ExponentialBackoff(
            base_delay=1.0,
            max_delay=100.0,
            max_attempts=5,
            jitter=True
        )
        
        # Get multiple delays and check they're different (due to jitter)
        delays = [backoff.get_delay() for _ in range(10)]
        
        # Should have some variation
        assert len(set(delays)) > 1
        
        # All should be within reasonable range (0.75 to 1.25 for attempt 0)
        for delay in delays:
            assert 0.5 <= delay <= 1.5
    
    def test_sleep_increments_attempt(self):
        """Test that sleep increments attempt counter."""
        backoff = ExponentialBackoff(base_delay=0.01, max_delay=1.0, max_attempts=3)
        
        assert backoff.attempt == 0
        backoff.sleep()
        assert backoff.attempt == 1
        backoff.sleep()
        assert backoff.attempt == 2
    
    def test_sleep_returns_false_at_max_attempts(self):
        """Test that sleep returns False when max attempts reached."""
        backoff = ExponentialBackoff(base_delay=0.01, max_delay=1.0, max_attempts=2)
        
        assert backoff.sleep() is True  # Attempt 1
        assert backoff.sleep() is True  # Attempt 2
        assert backoff.sleep() is False  # Max reached
    
    def test_reset(self):
        """Test that reset resets attempt counter."""
        backoff = ExponentialBackoff(base_delay=0.01, max_delay=1.0, max_attempts=5)
        
        backoff.sleep()
        backoff.sleep()
        assert backoff.attempt == 2
        
        backoff.reset()
        assert backoff.attempt == 0


class TestDatabaseConnectionManager:
    """Test DatabaseConnectionManager class."""
    
    @patch('stockiq.infrastructure.connection_pool.get_engine')
    def test_initialization(self, mock_get_engine):
        """Test database connection manager initialization."""
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        
        manager = DatabaseConnectionManager()
        
        assert manager.engine == mock_engine
        assert manager._connection_attempts == 0
        assert manager._last_connection_error is None
    
    @patch('stockiq.infrastructure.connection_pool.get_db_context')
    @patch('stockiq.infrastructure.connection_pool.get_engine')
    def test_get_session_with_retry_success(self, mock_get_engine, mock_get_db_context):
        """Test successful session creation with retry."""
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        
        mock_session = Mock()
        mock_session.execute.return_value = None
        mock_get_db_context.return_value.__enter__.return_value = mock_session
        mock_get_db_context.return_value.__exit__.return_value = False
        
        manager = DatabaseConnectionManager()
        
        with manager.get_session_with_retry() as session:
            assert session == mock_session
    
    @patch('stockiq.infrastructure.connection_pool.get_db_context')
    @patch('stockiq.infrastructure.connection_pool.get_engine')
    def test_get_session_with_retry_recovers_after_failure(
        self, mock_get_engine, mock_get_db_context
    ):
        """Test that session creation recovers after transient failure."""
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        
        mock_session = Mock()
        mock_session.execute.side_effect = [
            OperationalError("Connection failed", None, None),  # First attempt fails
            None,  # Second attempt succeeds
        ]
        
        mock_get_db_context.return_value.__enter__.return_value = mock_session
        mock_get_db_context.return_value.__exit__.return_value = False
        
        manager = DatabaseConnectionManager()
        
        # Should succeed after retry
        with manager.get_session_with_retry(max_retries=3) as session:
            assert session == mock_session
    
    @patch('stockiq.infrastructure.connection_pool.get_db_context')
    @patch('stockiq.infrastructure.connection_pool.get_engine')
    def test_get_session_with_retry_fails_after_max_retries(
        self, mock_get_engine, mock_get_db_context
    ):
        """Test that session creation fails after max retries."""
        mock_engine = Mock()
        mock_engine.dispose = Mock()
        mock_get_engine.return_value = mock_engine
        
        mock_session = Mock()
        mock_session.execute.side_effect = OperationalError("Connection failed", None, None)
        
        mock_get_db_context.return_value.__enter__.return_value = mock_session
        mock_get_db_context.return_value.__exit__.return_value = False
        
        manager = DatabaseConnectionManager()
        
        # Should raise after max retries
        with pytest.raises(OperationalError):
            with manager.get_session_with_retry(max_retries=2) as session:
                pass
    
    @patch('stockiq.infrastructure.connection_pool.get_db_context')
    @patch('stockiq.infrastructure.connection_pool.get_engine')
    def test_test_connection_success(self, mock_get_engine, mock_get_db_context):
        """Test connection health check success."""
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        
        mock_session = Mock()
        mock_session.execute.return_value = None
        mock_get_db_context.return_value.__enter__.return_value = mock_session
        mock_get_db_context.return_value.__exit__.return_value = False
        
        manager = DatabaseConnectionManager()
        
        assert manager.test_connection() is True
    
    @patch('stockiq.infrastructure.connection_pool.get_db_context')
    @patch('stockiq.infrastructure.connection_pool.get_engine')
    def test_test_connection_failure(self, mock_get_engine, mock_get_db_context):
        """Test connection health check failure."""
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        
        mock_get_db_context.side_effect = OperationalError("Connection failed", None, None)
        
        manager = DatabaseConnectionManager()
        
        assert manager.test_connection() is False
    
    @patch('stockiq.infrastructure.connection_pool.get_engine')
    def test_get_pool_status(self, mock_get_engine):
        """Test getting connection pool status."""
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 8
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        mock_get_engine.return_value = mock_engine
        
        manager = DatabaseConnectionManager()
        status = manager.get_pool_status()
        
        assert status['size'] == 10
        assert status['checked_in'] == 8
        assert status['checked_out'] == 2
        assert status['overflow'] == 0


class TestCacheConnectionManager:
    """Test CacheConnectionManager class."""
    
    def test_initialization(self):
        """Test cache connection manager initialization."""
        manager = CacheConnectionManager()
        
        assert manager._connection_attempts == 0
        assert manager._last_connection_error is None
    
    def test_execute_with_retry_success(self):
        """Test successful operation execution."""
        manager = CacheConnectionManager()
        
        operation = Mock(return_value="success")
        result = manager.execute_with_retry(operation, max_retries=3)
        
        assert result == "success"
        operation.assert_called_once()
    
    def test_execute_with_retry_recovers_after_failure(self):
        """Test that operation recovers after transient failure."""
        manager = CacheConnectionManager()
        
        operation = Mock(side_effect=[
            Exception("Connection failed"),  # First attempt fails
            "success",  # Second attempt succeeds
        ])
        
        result = manager.execute_with_retry(operation, max_retries=3)
        
        assert result == "success"
        assert operation.call_count == 2
    
    def test_execute_with_retry_fails_after_max_retries(self):
        """Test that operation fails after max retries."""
        manager = CacheConnectionManager()
        
        operation = Mock(side_effect=Exception("Connection failed"))
        
        result = manager.execute_with_retry(operation, max_retries=2)
        
        assert result is None  # Returns None on failure
    
    @patch('stockiq.infrastructure.connection_pool.get_cache')
    def test_test_connection_success(self, mock_get_cache):
        """Test cache connection health check success."""
        mock_cache = Mock()
        mock_cache.set.return_value = None
        mock_cache.get.return_value = "ok"
        mock_get_cache.return_value = mock_cache
        
        manager = CacheConnectionManager()
        
        assert manager.test_connection() is True
    
    @patch('stockiq.infrastructure.connection_pool.get_cache')
    def test_test_connection_failure(self, mock_get_cache):
        """Test cache connection health check failure."""
        mock_cache = Mock()
        mock_cache.set.side_effect = Exception("Connection failed")
        mock_get_cache.return_value = mock_cache
        
        manager = CacheConnectionManager()
        
        assert manager.test_connection() is False


class TestGlobalFunctions:
    """Test global helper functions."""
    
    @patch('stockiq.infrastructure.connection_pool.get_db_connection_manager')
    def test_db_session_with_retry(self, mock_get_manager):
        """Test db_session_with_retry context manager."""
        mock_manager = Mock()
        mock_session = Mock()
        
        # Create a proper context manager mock
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_session
        mock_context.__exit__.return_value = False
        
        mock_manager.get_session_with_retry.return_value = mock_context
        mock_get_manager.return_value = mock_manager
        
        with db_session_with_retry() as session:
            assert session == mock_session
    
    def test_execute_cache_operation_with_retry(self):
        """Test execute_cache_operation_with_retry."""
        mock_manager = Mock()
        mock_manager.execute_with_retry.return_value = "result"
        
        with patch(
            'stockiq.infrastructure.connection_pool.get_cache_connection_manager',
            return_value=mock_manager
        ):
            operation = Mock()
            result = execute_cache_operation_with_retry(operation, max_retries=3)
            
            mock_manager.execute_with_retry.assert_called_once_with(operation, max_retries=3)


class TestExponentialBackoffIntegration:
    """Integration tests for exponential backoff."""
    
    def test_backoff_timing(self):
        """Test that backoff actually sleeps for expected duration."""
        backoff = ExponentialBackoff(
            base_delay=0.1,
            max_delay=1.0,
            max_attempts=3,
            jitter=False
        )
        
        # First sleep should be ~0.1 seconds
        start = time.time()
        backoff.sleep()
        elapsed = time.time() - start
        
        assert 0.08 <= elapsed <= 0.15  # Allow some tolerance
        
        # Second sleep should be ~0.2 seconds
        start = time.time()
        backoff.sleep()
        elapsed = time.time() - start
        
        assert 0.18 <= elapsed <= 0.25
    
    def test_max_attempts_behavior(self):
        """Test behavior at max attempts."""
        backoff = ExponentialBackoff(
            base_delay=0.01,
            max_delay=0.1,
            max_attempts=2
        )
        
        attempts = 0
        while backoff.sleep():
            attempts += 1
        
        # Should stop after max_attempts
        assert attempts == 2
        assert backoff.attempt == 2
