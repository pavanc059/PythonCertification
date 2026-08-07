"""
Tests for security hardening implementation.

Tests cover:
- Input validation (tickers, dates, numbers)
- Parameterized queries and SQL injection prevention
- API key rotation and secrets management
- Rate limiting per user
- Integration with existing security infrastructure
"""

import pytest
import os
from datetime import date, datetime, timedelta
from decimal import Decimal

# Set up environment for tests
os.environ.setdefault('DATABASE_URL', 'postgresql://user:password@localhost:5432/test_db')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('SECRET_KEY', 'test_secret_key')
os.environ.setdefault('JWT_SECRET_KEY', 'test_jwt_secret_key')

# Import validation functions
from stockiq.core.validation import (
    validate_ticker,
    validate_ticker_list,
    validate_date,
    validate_date_range,
    validate_integer,
    validate_float,
    validate_decimal,
    validate_percentage,
    validate_email,
    validate_url,
    validate_string_length,
    validate_choice,
    is_valid_ticker,
    is_valid_date,
    is_valid_email,
    ValidationError,
    TickerValidationError,
    DateValidationError,
    NumericValidationError,
)

# Import secrets management
from stockiq.infrastructure.secrets import (
    SecretsManager,
    APIKeyManager,
    get_secrets_manager,
    get_api_key_manager,
    get_api_key,
    SecretNotFoundError,
    SecretExpiredError,
)

# Import database utilities
from stockiq.infrastructure.database import (
    build_safe_filter,
    build_safe_query,
    _is_safe_identifier,
    _is_parameterized_query,
)

# Import rate limiter
from stockiq.infrastructure.rate_limiter import RateLimiter


# ============================================================================
# Ticker Validation Tests
# ============================================================================

class TestTickerValidation:
    """Tests for ticker validation."""
    
    def test_valid_tickers(self):
        """Test validation of valid tickers."""
        assert validate_ticker("AAPL") == "AAPL"
        assert validate_ticker("TSLA") == "TSLA"
        assert validate_ticker("MSFT") == "MSFT"
        assert validate_ticker("BRK.A") == "BRK.A"
        assert validate_ticker("  aapl  ") == "AAPL"  # Normalization
    
    def test_invalid_tickers(self):
        """Test rejection of invalid tickers."""
        with pytest.raises(TickerValidationError):
            validate_ticker("")  # Empty
        
        with pytest.raises(TickerValidationError):
            validate_ticker("TOOLONG")  # Too long
        
        with pytest.raises(TickerValidationError):
            validate_ticker("123")  # Numbers only
        
        with pytest.raises(TickerValidationError):
            validate_ticker("AA$L")  # Special chars
    
    def test_crypto_tickers(self):
        """Test cryptocurrency ticker validation."""
        assert validate_ticker("BTC-USD", allow_crypto=True) == "BTC-USD"
        assert validate_ticker("ETH-USDT", allow_crypto=True) == "ETH-USDT"
        
        with pytest.raises(TickerValidationError):
            validate_ticker("BTC-USD", allow_crypto=False)
    
    def test_ticker_list_validation(self):
        """Test validation of ticker lists."""
        # From string
        result = validate_ticker_list("AAPL,TSLA,MSFT")
        assert result == ["AAPL", "TSLA", "MSFT"]
        
        # From list
        result = validate_ticker_list(["AAPL", "TSLA"])
        assert result == ["AAPL", "TSLA"]
        
        # Deduplication
        result = validate_ticker_list("AAPL,AAPL,TSLA")
        assert result == ["AAPL", "TSLA"]
    
    def test_ticker_list_max_count(self):
        """Test ticker list maximum count enforcement."""
        tickers = ["TICK" + str(i) for i in range(101)]
        
        with pytest.raises(TickerValidationError):
            validate_ticker_list(tickers, max_count=100)
    
    def test_is_valid_ticker_helper(self):
        """Test ticker validation helper function."""
        assert is_valid_ticker("AAPL") is True
        assert is_valid_ticker("INVALID123") is False
        assert is_valid_ticker("") is False


# ============================================================================
# Date Validation Tests
# ============================================================================

class TestDateValidation:
    """Tests for date validation."""
    
    def test_valid_dates(self):
        """Test validation of valid dates."""
        # String formats
        assert validate_date("2024-01-15") == date(2024, 1, 15)
        assert validate_date("2024/01/15") == date(2024, 1, 15)
        assert validate_date("01-15-2024") == date(2024, 1, 15)
        
        # Date object
        d = date(2024, 1, 15)
        assert validate_date(d) == d
        
        # Datetime object
        dt = datetime(2024, 1, 15, 10, 30)
        assert validate_date(dt) == date(2024, 1, 15)
    
    def test_invalid_date_formats(self):
        """Test rejection of invalid date formats."""
        with pytest.raises(DateValidationError):
            validate_date("not-a-date")
        
        with pytest.raises(DateValidationError):
            validate_date("2024-13-01")  # Invalid month
        
        with pytest.raises(DateValidationError):
            validate_date(123)  # Invalid type
    
    def test_future_date_validation(self):
        """Test future date rejection."""
        future_date = (date.today() + timedelta(days=7)).isoformat()
        
        # Should reject by default
        with pytest.raises(DateValidationError):
            validate_date(future_date, allow_future=False)
        
        # Should allow if specified
        result = validate_date(future_date, allow_future=True)
        assert result > date.today()
    
    def test_date_bounds(self):
        """Test date minimum/maximum bounds."""
        min_date = date(2020, 1, 1)
        max_date = date(2024, 12, 31)
        
        # Valid within bounds
        result = validate_date("2022-06-15", min_date=min_date, max_date=max_date)
        assert min_date <= result <= max_date
        
        # Below minimum
        with pytest.raises(DateValidationError):
            validate_date("2019-12-31", min_date=min_date)
        
        # Above maximum
        with pytest.raises(DateValidationError):
            validate_date("2025-01-01", max_date=max_date)
    
    def test_date_range_validation(self):
        """Test date range validation."""
        start, end = validate_date_range("2024-01-01", "2024-01-31")
        assert start == date(2024, 1, 1)
        assert end == date(2024, 1, 31)
        
        # Invalid order
        with pytest.raises(DateValidationError):
            validate_date_range("2024-01-31", "2024-01-01")
    
    def test_date_range_max_days(self):
        """Test date range maximum days enforcement."""
        # Within limit
        start, end = validate_date_range(
            "2024-01-01",
            "2024-01-10",
            max_days=30
        )
        assert (end - start).days == 9
        
        # Exceeds limit
        with pytest.raises(DateValidationError):
            validate_date_range(
                "2024-01-01",
                "2024-03-01",
                max_days=30
            )


# ============================================================================
# Numeric Validation Tests
# ============================================================================

class TestNumericValidation:
    """Tests for numeric validation."""
    
    def test_integer_validation(self):
        """Test integer validation."""
        assert validate_integer(42) == 42
        assert validate_integer("42") == 42
        assert validate_integer(42.0) == 42
        
        with pytest.raises(NumericValidationError):
            validate_integer("not a number")
        
        with pytest.raises(NumericValidationError):
            validate_integer(True)  # Booleans not allowed
    
    def test_integer_bounds(self):
        """Test integer bounds checking."""
        assert validate_integer(50, min_value=0, max_value=100) == 50
        
        with pytest.raises(NumericValidationError):
            validate_integer(-1, min_value=0)
        
        with pytest.raises(NumericValidationError):
            validate_integer(101, max_value=100)
    
    def test_float_validation(self):
        """Test float validation."""
        assert validate_float(3.14) == 3.14
        assert validate_float("3.14") == 3.14
        assert validate_float(42) == 42.0
        
        with pytest.raises(NumericValidationError):
            validate_float("not a number")
    
    def test_float_special_values(self):
        """Test float special value handling."""
        # NaN
        with pytest.raises(NumericValidationError):
            validate_float(float('nan'), allow_nan=False)
        
        result = validate_float(float('nan'), allow_nan=True)
        assert result != result  # NaN != NaN
        
        # Infinity
        with pytest.raises(NumericValidationError):
            validate_float(float('inf'), allow_inf=False)
        
        result = validate_float(float('inf'), allow_inf=True)
        assert result == float('inf')
    
    def test_decimal_validation(self):
        """Test decimal validation for financial precision."""
        result = validate_decimal("199.99")
        assert result == Decimal("199.99")
        
        result = validate_decimal(42)
        assert result == Decimal("42")
        
        with pytest.raises(NumericValidationError):
            validate_decimal("not a number")
    
    def test_decimal_precision(self):
        """Test decimal precision enforcement."""
        # Within limits
        result = validate_decimal(
            "123.45",
            max_digits=5,
            decimal_places=2
        )
        assert result == Decimal("123.45")
        
        # Exceeds decimal places
        with pytest.raises(NumericValidationError):
            validate_decimal(
                "123.456",
                decimal_places=2
            )
    
    def test_percentage_validation(self):
        """Test percentage validation."""
        assert validate_percentage(50.5) == 50.5
        assert validate_percentage("99") == 99.0
        
        with pytest.raises(NumericValidationError):
            validate_percentage(-1)  # Below 0
        
        with pytest.raises(NumericValidationError):
            validate_percentage(101)  # Above 100


# ============================================================================
# String Validation Tests
# ============================================================================

class TestStringValidation:
    """Tests for string validation."""
    
    def test_email_validation(self):
        """Test email validation."""
        assert validate_email("user@example.com") == "user@example.com"
        assert validate_email("  USER@EXAMPLE.COM  ") == "user@example.com"
        
        with pytest.raises(ValidationError):
            validate_email("not-an-email")
        
        with pytest.raises(ValidationError):
            validate_email("@example.com")
        
        with pytest.raises(ValidationError):
            validate_email("user@")
    
    def test_url_validation(self):
        """Test URL validation."""
        assert validate_url("https://example.com") == "https://example.com"
        assert validate_url("http://example.com") == "http://example.com"
        
        with pytest.raises(ValidationError):
            validate_url("not-a-url")
        
        with pytest.raises(ValidationError):
            validate_url("javascript:alert('xss')")  # Blocked scheme
    
    def test_string_length_validation(self):
        """Test string length validation."""
        assert validate_string_length("hello", min_length=1, max_length=10) == "hello"
        
        with pytest.raises(ValidationError):
            validate_string_length("", allow_empty=False)
        
        with pytest.raises(ValidationError):
            validate_string_length("x" * 101, max_length=100)
    
    def test_choice_validation(self):
        """Test choice validation."""
        assert validate_choice("red", ["red", "green", "blue"]) == "red"
        
        # Case insensitive
        assert validate_choice(
            "RED",
            ["red", "green", "blue"],
            case_sensitive=False
        ) == "red"
        
        with pytest.raises(ValidationError):
            validate_choice("yellow", ["red", "green", "blue"])


# ============================================================================
# SQL Injection Prevention Tests
# ============================================================================

class TestSQLInjectionPrevention:
    """Tests for SQL injection prevention in database utilities."""
    
    def test_safe_identifier_validation(self):
        """Test identifier (table/column name) validation."""
        assert _is_safe_identifier("table_name") is True
        assert _is_safe_identifier("column123") is True
        assert _is_safe_identifier("_private") is True
        
        # SQL injection attempts
        assert _is_safe_identifier("table; DROP TABLE users;") is False
        assert _is_safe_identifier("1table") is False
        assert _is_safe_identifier("table-name") is False
    
    def test_parameterized_query_detection(self):
        """Test detection of parameterized queries."""
        # Valid parameterized query
        assert _is_parameterized_query(
            "SELECT * FROM stocks WHERE ticker = :ticker"
        ) is True
        
        # Dangerous patterns
        assert _is_parameterized_query(
            "SELECT * FROM stocks WHERE ticker = '" + "AAPL" + "'"
        ) is False
        
        assert _is_parameterized_query(
            "SELECT * FROM stocks WHERE ticker = %s"
        ) is False
    
    def test_build_safe_filter(self):
        """Test safe filter clause building."""
        clause, params = build_safe_filter("ticker", "=", "AAPL")
        assert "ticker = :ticker_filter" in clause
        assert params["ticker_filter"] == "AAPL"
        
        # IN operator
        clause, params = build_safe_filter("ticker", "IN", ["AAPL", "TSLA"])
        assert "ticker IN" in clause
        assert len(params) == 2
    
    def test_build_safe_query(self):
        """Test safe SELECT query building."""
        query, params = build_safe_query(
            "stocks",
            ["ticker", "price"],
            filters=[("market_cap", ">", 1000000)],
            order_by=[("ticker", "ASC")],
            limit=10
        )
        
        assert "SELECT ticker, price FROM stocks" in query
        assert "WHERE" in query
        assert "ORDER BY ticker ASC" in query
        assert "LIMIT 10" in query
        assert len(params) > 0
    
    def test_sql_injection_blocked(self):
        """Test that SQL injection attempts are blocked."""
        # Invalid column name with SQL injection
        with pytest.raises(ValueError):
            build_safe_query(
                "stocks",
                ["ticker; DROP TABLE stocks;"]
            )
        
        # Invalid table name
        with pytest.raises(ValueError):
            build_safe_query(
                "stocks; DROP TABLE users;",
                ["ticker"]
            )


# ============================================================================
# Secrets Management Tests
# ============================================================================

class TestSecretsManager:
    """Tests for secrets management."""
    
    def test_secrets_manager_initialization(self):
        """Test secrets manager initialization."""
        manager = SecretsManager()
        assert manager is not None
    
    def test_set_and_get_secret(self):
        """Test setting and retrieving secrets."""
        manager = SecretsManager()
        manager.set_secret("TEST_SECRET", "secret_value")
        
        value = manager.get_secret("TEST_SECRET")
        assert value == "secret_value"
    
    def test_secret_not_found(self):
        """Test handling of missing secrets."""
        manager = SecretsManager()
        
        with pytest.raises(SecretNotFoundError):
            manager.get_secret("NONEXISTENT_SECRET")
    
    def test_secret_expiry(self):
        """Test secret expiry handling."""
        manager = SecretsManager()
        manager.set_secret("EXPIRING_SECRET", "value", expires_in_days=-1)
        
        with pytest.raises(SecretExpiredError):
            manager.get_secret("EXPIRING_SECRET")
    
    def test_secret_rotation(self):
        """Test secret rotation with grace period."""
        manager = SecretsManager()
        manager.set_secret("API_KEY", "old_value")
        
        # Rotate
        manager.rotate_secret("API_KEY", "new_value", grace_period_days=7)
        
        # New value should be active
        assert manager.get_secret("API_KEY") == "new_value"
        
        # Old value should still exist during grace period
        assert "API_KEY_OLD" in manager._secrets
    
    def test_secret_validation(self):
        """Test secret value validation."""
        manager = SecretsManager()
        manager.set_secret("API_KEY", "correct_value")
        
        assert manager.validate_secret("API_KEY", "correct_value") is True
        assert manager.validate_secret("API_KEY", "wrong_value") is False
    
    def test_secret_masking(self):
        """Test secret value masking for logs."""
        manager = SecretsManager()
        
        masked = manager.mask_secret("secret_key_12345")
        assert masked == "secr...2345"
        assert "secret_key_12345" not in masked
    
    def test_list_secrets(self):
        """Test listing available secrets."""
        manager = SecretsManager()
        manager.set_secret("SECRET_1", "value1")
        manager.set_secret("SECRET_2", "value2")
        
        secrets = manager.list_secrets()
        assert "SECRET_1" in secrets
        assert "SECRET_2" in secrets
    
    def test_cleanup_old_secrets(self):
        """Test cleanup of expired old secrets."""
        manager = SecretsManager()
        manager.set_secret("API_KEY", "old_value")
        manager.rotate_secret("API_KEY", "new_value", grace_period_days=-1)
        
        # Cleanup should remove expired old secret
        removed = manager.cleanup_old_secrets()
        assert removed == 1
        assert "API_KEY_OLD" not in manager._secrets


class TestAPIKeyManager:
    """Tests for API key management."""
    
    def test_api_key_manager_initialization(self):
        """Test API key manager initialization."""
        manager = APIKeyManager()
        assert manager is not None
    
    def test_list_services(self):
        """Test listing supported services."""
        manager = APIKeyManager()
        services = manager.list_services()
        
        assert "newsapi" in services
        assert "finnhub" in services
        assert "alpha_vantage" in services
    
    def test_get_masked_api_key(self):
        """Test getting masked API key for display."""
        manager = APIKeyManager()
        # Set a test key
        manager.secrets.set_secret("NEWSAPI_API_KEY", "test_key_12345")
        
        masked = manager.get_masked_api_key("newsapi")
        assert "***" in masked or "..." in masked
        assert "test_key_12345" not in masked


# ============================================================================
# Rate Limiting Tests
# ============================================================================

class TestRateLimiting:
    """Tests for rate limiting functionality."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(
            source="test",
            max_requests=100,
            time_window=3600
        )
        assert limiter.threshold == 80  # 80% of max
    
    def test_rate_limit_allows_requests(self):
        """Test that rate limiter allows requests within limit."""
        limiter = RateLimiter(source="test", max_requests=10, time_window=3600)
        
        # Should allow first few requests
        assert limiter.is_allowed() is True
    
    def test_rate_limit_acquire(self):
        """Test acquiring rate limit tokens."""
        limiter = RateLimiter(source="test", max_requests=5, time_window=3600)
        
        # Acquire tokens
        for i in range(4):  # 80% of 5 = 4
            assert limiter.acquire() is True
        
        # Should block after threshold
        assert limiter.acquire() is False
    
    def test_rate_limit_remaining(self):
        """Test getting remaining requests."""
        limiter = RateLimiter(source="test", max_requests=10, time_window=3600)
        
        remaining = limiter.get_remaining()
        assert remaining == 8  # 80% of 10
        
        limiter.acquire()
        remaining = limiter.get_remaining()
        assert remaining == 7


# ============================================================================
# Integration Tests
# ============================================================================

class TestSecurityIntegration:
    """Integration tests for security features."""
    
    def test_ticker_validation_in_query_building(self):
        """Test ticker validation integrated with query building."""
        # Validate ticker
        ticker = validate_ticker("AAPL")
        
        # Use in safe query
        query, params = build_safe_query(
            "stocks",
            ["price", "volume"],
            filters=[("ticker", "=", ticker)],
            limit=1
        )
        
        assert "ticker" in query
        assert ticker in params.values()
    
    def test_date_validation_in_query_building(self):
        """Test date validation integrated with query building."""
        # Validate date range
        start, end = validate_date_range("2024-01-01", "2024-01-31")
        
        # Use in safe query
        clause1, params1 = build_safe_filter("date", ">=", start)
        clause2, params2 = build_safe_filter("date", "<=", end)
        
        assert "date" in clause1
        assert "date" in clause2
    
    def test_numeric_validation_for_parameters(self):
        """Test numeric validation for query parameters."""
        # Validate numeric inputs
        limit = validate_integer(10, min_value=1, max_value=100)
        price_threshold = validate_decimal("100.00", min_value=0)
        
        # Use in query
        query, params = build_safe_query(
            "stocks",
            ["ticker", "price"],
            filters=[("price", ">", float(price_threshold))],
            limit=limit
        )
        
        assert f"LIMIT {limit}" in query


# ============================================================================
# Helper Functions Tests
# ============================================================================

class TestHelperFunctions:
    """Tests for helper validation functions."""
    
    def test_is_valid_ticker(self):
        """Test ticker validation helper."""
        assert is_valid_ticker("AAPL") is True
        assert is_valid_ticker("INVALID$") is False
    
    def test_is_valid_date(self):
        """Test date validation helper."""
        assert is_valid_date("2024-01-15") is True
        assert is_valid_date("invalid") is False
    
    def test_is_valid_email(self):
        """Test email validation helper."""
        assert is_valid_email("user@example.com") is True
        assert is_valid_email("not-an-email") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
