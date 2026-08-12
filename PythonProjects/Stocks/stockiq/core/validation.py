"""
Input validation utilities for the StockIQ application.

This module provides comprehensive input validation functions for:
- Stock tickers
- Date ranges
- Numeric parameters
- Email addresses
- URLs
- User inputs

All validation functions prevent injection attacks and ensure data integrity.
"""

import re
from datetime import datetime, date, timedelta
from typing import Any, Optional, Union, List, Tuple
from decimal import Decimal, InvalidOperation
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# Validation Exceptions
# ============================================================================

class ValidationError(ValueError):
    """Base exception for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field
        self.message = message


class TickerValidationError(ValidationError):
    """Exception for invalid ticker symbols."""
    pass


class DateValidationError(ValidationError):
    """Exception for invalid date inputs."""
    pass


class NumericValidationError(ValidationError):
    """Exception for invalid numeric inputs."""
    pass


# ============================================================================
# Ticker Validation
# ============================================================================

def validate_ticker(
    ticker: str,
    allow_crypto: bool = False,
    allow_forex: bool = False
) -> str:
    """
    Validate and normalize a stock ticker symbol.
    
    Args:
        ticker: Stock ticker symbol
        allow_crypto: Whether to allow cryptocurrency symbols
        allow_forex: Whether to allow forex pairs
        
    Returns:
        Normalized ticker (uppercase, trimmed)
        
    Raises:
        TickerValidationError: If ticker is invalid
        
    Examples:
        >>> validate_ticker("AAPL")
        'AAPL'
        >>> validate_ticker("  tsla  ")
        'TSLA'
        >>> validate_ticker("BTC-USD", allow_crypto=True)
        'BTC-USD'
    """
    if not ticker or not isinstance(ticker, str):
        raise TickerValidationError("Ticker must be a non-empty string", field="ticker")
    
    # Normalize: uppercase and strip
    ticker = ticker.upper().strip()
    
    # Check length
    if len(ticker) < 1 or len(ticker) > 10:
        raise TickerValidationError(
            f"Ticker must be 1-10 characters, got {len(ticker)}",
            field="ticker"
        )
    
    # Standard stock ticker: 1-5 uppercase letters
    stock_pattern = r'^[A-Z]{1,5}$'
    
    # Stock with exchange suffix: TICKER.EXCHANGE
    stock_exchange_pattern = r'^[A-Z]{1,5}\.[A-Z]{1,3}$'
    
    # Cryptocurrency: XXX-USD, XXX-USDT, etc.
    crypto_pattern = r'^[A-Z]{2,5}-[A-Z]{3,5}$'
    
    # Forex pair: XXXYYY or XXX/YYY
    forex_pattern = r'^[A-Z]{6}$|^[A-Z]{3}/[A-Z]{3}$'
    
    # Check patterns
    if re.match(stock_pattern, ticker) or re.match(stock_exchange_pattern, ticker):
        return ticker
    
    if allow_crypto and re.match(crypto_pattern, ticker):
        return ticker
    
    if allow_forex and re.match(forex_pattern, ticker):
        return ticker
    
    # Invalid format
    raise TickerValidationError(
        f"Invalid ticker format: {ticker}. Expected 1-5 uppercase letters",
        field="ticker"
    )


def validate_ticker_list(
    tickers: Union[str, List[str]],
    allow_crypto: bool = False,
    allow_forex: bool = False,
    max_count: int = 100
) -> List[str]:
    """
    Validate and normalize a list of tickers.
    
    Args:
        tickers: Single ticker or list of tickers
        allow_crypto: Whether to allow cryptocurrency symbols
        allow_forex: Whether to allow forex pairs
        max_count: Maximum number of tickers allowed
        
    Returns:
        List of normalized tickers
        
    Raises:
        TickerValidationError: If any ticker is invalid
        
    Examples:
        >>> validate_ticker_list("AAPL,TSLA,MSFT")
        ['AAPL', 'TSLA', 'MSFT']
        >>> validate_ticker_list(["AAPL", "TSLA"])
        ['AAPL', 'TSLA']
    """
    # Convert string to list if needed
    if isinstance(tickers, str):
        # Split on comma or whitespace
        tickers = [t.strip() for t in re.split(r'[,\s]+', tickers) if t.strip()]
    
    if not isinstance(tickers, list):
        raise TickerValidationError("Tickers must be a string or list", field="tickers")
    
    if len(tickers) == 0:
        raise TickerValidationError("At least one ticker is required", field="tickers")
    
    if len(tickers) > max_count:
        raise TickerValidationError(
            f"Too many tickers: {len(tickers)} (max {max_count})",
            field="tickers"
        )
    
    # Validate each ticker
    validated = []
    for ticker in tickers:
        validated.append(validate_ticker(ticker, allow_crypto, allow_forex))
    
    # Remove duplicates while preserving order
    seen = set()
    deduplicated = []
    for ticker in validated:
        if ticker not in seen:
            seen.add(ticker)
            deduplicated.append(ticker)
    
    return deduplicated


# ============================================================================
# Date Validation
# ============================================================================

def validate_date(
    date_input: Union[str, date, datetime],
    field_name: str = "date",
    allow_future: bool = False,
    min_date: Optional[date] = None,
    max_date: Optional[date] = None
) -> date:
    """
    Validate and parse a date input.
    
    Args:
        date_input: Date as string (YYYY-MM-DD), date, or datetime object
        field_name: Name of the field (for error messages)
        allow_future: Whether to allow future dates
        min_date: Minimum allowed date
        max_date: Maximum allowed date
        
    Returns:
        date object
        
    Raises:
        DateValidationError: If date is invalid
        
    Examples:
        >>> validate_date("2024-01-15")
        datetime.date(2024, 1, 15)
        >>> validate_date(datetime(2024, 1, 15))
        datetime.date(2024, 1, 15)
    """
    # Convert to date object
    if isinstance(date_input, datetime):
        parsed_date = date_input.date()
    elif isinstance(date_input, date):
        parsed_date = date_input
    elif isinstance(date_input, str):
        # Try common date formats
        formats = [
            '%Y-%m-%d',      # 2024-01-15
            '%Y/%m/%d',      # 2024/01/15
            '%m-%d-%Y',      # 01-15-2024
            '%m/%d/%Y',      # 01/15/2024
            '%d-%m-%Y',      # 15-01-2024
            '%d/%m/%Y',      # 15/01/2024
        ]
        
        parsed_date = None
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_input.strip(), fmt).date()
                break
            except ValueError:
                continue
        
        if parsed_date is None:
            raise DateValidationError(
                f"Invalid date format for {field_name}: {date_input}. Expected YYYY-MM-DD",
                field=field_name
            )
    else:
        raise DateValidationError(
            f"Invalid type for {field_name}: expected string, date, or datetime",
            field=field_name
        )
    
    # Check if future
    if not allow_future and parsed_date > date.today():
        raise DateValidationError(
            f"Future dates not allowed for {field_name}: {parsed_date}",
            field=field_name
        )
    
    # Check min/max bounds
    if min_date and parsed_date < min_date:
        raise DateValidationError(
            f"{field_name} must be on or after {min_date}, got {parsed_date}",
            field=field_name
        )
    
    if max_date and parsed_date > max_date:
        raise DateValidationError(
            f"{field_name} must be on or before {max_date}, got {parsed_date}",
            field=field_name
        )
    
    return parsed_date


def validate_date_range(
    start_date: Union[str, date, datetime],
    end_date: Union[str, date, datetime],
    max_days: Optional[int] = None,
    allow_future: bool = False
) -> Tuple[date, date]:
    """
    Validate a date range.
    
    Args:
        start_date: Start date
        end_date: End date
        max_days: Maximum number of days in range
        allow_future: Whether to allow future dates
        
    Returns:
        Tuple of (start_date, end_date)
        
    Raises:
        DateValidationError: If date range is invalid
        
    Examples:
        >>> validate_date_range("2024-01-01", "2024-01-31")
        (datetime.date(2024, 1, 1), datetime.date(2024, 1, 31))
    """
    # Validate individual dates
    start = validate_date(start_date, "start_date", allow_future)
    end = validate_date(end_date, "end_date", allow_future)
    
    # Check order
    if start > end:
        raise DateValidationError(
            f"start_date ({start}) must be before end_date ({end})",
            field="date_range"
        )
    
    # Check maximum range
    if max_days:
        days_diff = (end - start).days
        if days_diff > max_days:
            raise DateValidationError(
                f"Date range exceeds maximum of {max_days} days: {days_diff} days",
                field="date_range"
            )
    
    return start, end


# ============================================================================
# Numeric Validation
# ============================================================================

def validate_integer(
    value: Any,
    field_name: str = "value",
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
    allow_none: bool = False
) -> Optional[int]:
    """
    Validate and convert to integer.
    
    Args:
        value: Value to validate
        field_name: Name of the field (for error messages)
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        allow_none: Whether None is allowed
        
    Returns:
        Integer value or None
        
    Raises:
        NumericValidationError: If value is invalid
        
    Examples:
        >>> validate_integer("42")
        42
        >>> validate_integer(42.0)
        42
        >>> validate_integer(None, allow_none=True)
        None
    """
    if value is None:
        if allow_none:
            return None
        raise NumericValidationError(f"{field_name} cannot be None", field=field_name)
    
    # Try to convert to int
    try:
        if isinstance(value, bool):
            raise NumericValidationError(
                f"{field_name} cannot be a boolean",
                field=field_name
            )
        int_value = int(value)
    except (ValueError, TypeError):
        raise NumericValidationError(
            f"Invalid integer for {field_name}: {value}",
            field=field_name
        )
    
    # Check bounds
    if min_value is not None and int_value < min_value:
        raise NumericValidationError(
            f"{field_name} must be >= {min_value}, got {int_value}",
            field=field_name
        )
    
    if max_value is not None and int_value > max_value:
        raise NumericValidationError(
            f"{field_name} must be <= {max_value}, got {int_value}",
            field=field_name
        )
    
    return int_value


def validate_float(
    value: Any,
    field_name: str = "value",
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    allow_none: bool = False,
    allow_nan: bool = False,
    allow_inf: bool = False
) -> Optional[float]:
    """
    Validate and convert to float.
    
    Args:
        value: Value to validate
        field_name: Name of the field (for error messages)
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        allow_none: Whether None is allowed
        allow_nan: Whether NaN is allowed
        allow_inf: Whether infinity is allowed
        
    Returns:
        Float value or None
        
    Raises:
        NumericValidationError: If value is invalid
        
    Examples:
        >>> validate_float("3.14")
        3.14
        >>> validate_float(42)
        42.0
    """
    if value is None:
        if allow_none:
            return None
        raise NumericValidationError(f"{field_name} cannot be None", field=field_name)
    
    # Try to convert to float
    try:
        if isinstance(value, bool):
            raise NumericValidationError(
                f"{field_name} cannot be a boolean",
                field=field_name
            )
        float_value = float(value)
    except (ValueError, TypeError):
        raise NumericValidationError(
            f"Invalid float for {field_name}: {value}",
            field=field_name
        )
    
    # Check for NaN
    if not allow_nan and float_value != float_value:  # NaN check
        raise NumericValidationError(
            f"{field_name} cannot be NaN",
            field=field_name
        )
    
    # Check for infinity
    if not allow_inf and (float_value == float('inf') or float_value == float('-inf')):
        raise NumericValidationError(
            f"{field_name} cannot be infinity",
            field=field_name
        )
    
    # Check bounds (skip if NaN or inf)
    if float_value == float_value and float_value != float('inf') and float_value != float('-inf'):
        if min_value is not None and float_value < min_value:
            raise NumericValidationError(
                f"{field_name} must be >= {min_value}, got {float_value}",
                field=field_name
            )
        
        if max_value is not None and float_value > max_value:
            raise NumericValidationError(
                f"{field_name} must be <= {max_value}, got {float_value}",
                field=field_name
            )
    
    return float_value


def validate_decimal(
    value: Any,
    field_name: str = "value",
    min_value: Optional[Union[Decimal, float, int]] = None,
    max_value: Optional[Union[Decimal, float, int]] = None,
    max_digits: Optional[int] = None,
    decimal_places: Optional[int] = None,
    allow_none: bool = False
) -> Optional[Decimal]:
    """
    Validate and convert to Decimal (for financial precision).
    
    Args:
        value: Value to validate
        field_name: Name of the field (for error messages)
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        max_digits: Maximum total digits
        decimal_places: Maximum decimal places
        allow_none: Whether None is allowed
        
    Returns:
        Decimal value or None
        
    Raises:
        NumericValidationError: If value is invalid
        
    Examples:
        >>> validate_decimal("199.99")
        Decimal('199.99')
        >>> validate_decimal(42)
        Decimal('42')
    """
    if value is None:
        if allow_none:
            return None
        raise NumericValidationError(f"{field_name} cannot be None", field=field_name)
    
    # Try to convert to Decimal
    try:
        if isinstance(value, bool):
            raise NumericValidationError(
                f"{field_name} cannot be a boolean",
                field=field_name
            )
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise NumericValidationError(
            f"Invalid decimal for {field_name}: {value}",
            field=field_name
        )
    
    # Check bounds
    if min_value is not None:
        min_decimal = Decimal(str(min_value))
        if decimal_value < min_decimal:
            raise NumericValidationError(
                f"{field_name} must be >= {min_value}, got {decimal_value}",
                field=field_name
            )
    
    if max_value is not None:
        max_decimal = Decimal(str(max_value))
        if decimal_value > max_decimal:
            raise NumericValidationError(
                f"{field_name} must be <= {max_value}, got {decimal_value}",
                field=field_name
            )
    
    # Check precision
    sign, digits, exponent = decimal_value.as_tuple()
    
    if max_digits is not None and len(digits) > max_digits:
        raise NumericValidationError(
            f"{field_name} exceeds maximum of {max_digits} digits",
            field=field_name
        )
    
    if decimal_places is not None:
        actual_places = -exponent if exponent < 0 else 0
        if actual_places > decimal_places:
            raise NumericValidationError(
                f"{field_name} exceeds maximum of {decimal_places} decimal places",
                field=field_name
            )
    
    return decimal_value


def validate_percentage(
    value: Any,
    field_name: str = "percentage",
    min_value: float = 0.0,
    max_value: float = 100.0,
    allow_none: bool = False
) -> Optional[float]:
    """
    Validate a percentage value (0-100).
    
    Args:
        value: Percentage value
        field_name: Name of the field (for error messages)
        min_value: Minimum percentage (default 0)
        max_value: Maximum percentage (default 100)
        allow_none: Whether None is allowed
        
    Returns:
        Float percentage or None
        
    Raises:
        NumericValidationError: If percentage is invalid
        
    Examples:
        >>> validate_percentage(75.5)
        75.5
        >>> validate_percentage("99")
        99.0
    """
    return validate_float(
        value,
        field_name=field_name,
        min_value=min_value,
        max_value=max_value,
        allow_none=allow_none
    )


# ============================================================================
# String Validation
# ============================================================================

def validate_email(email: str) -> str:
    """
    Validate email address format.
    
    Args:
        email: Email address
        
    Returns:
        Normalized email (lowercase, trimmed)
        
    Raises:
        ValidationError: If email is invalid
        
    Examples:
        >>> validate_email("user@example.com")
        'user@example.com'
        >>> validate_email("  USER@EXAMPLE.COM  ")
        'user@example.com'
    """
    if not email or not isinstance(email, str):
        raise ValidationError("Email must be a non-empty string", field="email")
    
    # Normalize
    email = email.lower().strip()
    
    # Basic email regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        raise ValidationError(f"Invalid email format: {email}", field="email")
    
    # Additional checks
    if len(email) > 254:  # RFC 5321
        raise ValidationError("Email address too long", field="email")
    
    local, domain = email.rsplit('@', 1)
    if len(local) > 64:  # RFC 5321
        raise ValidationError("Email local part too long", field="email")
    
    return email


def validate_url(
    url: str,
    allowed_schemes: Optional[List[str]] = None,
    require_tld: bool = True
) -> str:
    """
    Validate URL format.
    
    Args:
        url: URL string
        allowed_schemes: List of allowed URL schemes (default: ['http', 'https'])
        require_tld: Whether to require a top-level domain
        
    Returns:
        Normalized URL
        
    Raises:
        ValidationError: If URL is invalid
        
    Examples:
        >>> validate_url("https://example.com")
        'https://example.com'
    """
    if not url or not isinstance(url, str):
        raise ValidationError("URL must be a non-empty string", field="url")
    
    # Normalize
    url = url.strip()
    
    # Default allowed schemes
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']
    
    # Basic URL pattern
    pattern = r'^(https?|ftp)://[^\s/$.?#].[^\s]*$'
    
    if not re.match(pattern, url, re.IGNORECASE):
        raise ValidationError(f"Invalid URL format: {url}", field="url")
    
    # Extract scheme
    scheme = url.split('://')[0].lower()
    if scheme not in allowed_schemes:
        raise ValidationError(
            f"URL scheme '{scheme}' not allowed. Allowed: {allowed_schemes}",
            field="url"
        )
    
    # Check for TLD if required
    if require_tld:
        domain_part = url.split('://')[1].split('/')[0].split(':')[0]
        if '.' not in domain_part:
            raise ValidationError(
                "URL must include a top-level domain (e.g., .com, .org)",
                field="url"
            )
    
    return url


def validate_string_length(
    value: str,
    field_name: str = "value",
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    allow_empty: bool = False
) -> str:
    """
    Validate string length.
    
    Args:
        value: String value
        field_name: Name of the field (for error messages)
        min_length: Minimum length
        max_length: Maximum length
        allow_empty: Whether empty strings are allowed
        
    Returns:
        Validated string
        
    Raises:
        ValidationError: If string length is invalid
        
    Examples:
        >>> validate_string_length("hello", min_length=1, max_length=10)
        'hello'
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string", field=field_name)
    
    length = len(value)
    
    if not allow_empty and length == 0:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name)
    
    if min_length is not None and length < min_length:
        raise ValidationError(
            f"{field_name} must be at least {min_length} characters, got {length}",
            field=field_name
        )
    
    if max_length is not None and length > max_length:
        raise ValidationError(
            f"{field_name} must be at most {max_length} characters, got {length}",
            field=field_name
        )
    
    return value


# ============================================================================
# Enum/Choice Validation
# ============================================================================

def validate_choice(
    value: Any,
    choices: List[Any],
    field_name: str = "value",
    case_sensitive: bool = True
) -> Any:
    """
    Validate that value is one of the allowed choices.
    
    Args:
        value: Value to validate
        choices: List of allowed choices
        field_name: Name of the field (for error messages)
        case_sensitive: Whether comparison is case-sensitive (for strings)
        
    Returns:
        Validated value
        
    Raises:
        ValidationError: If value is not in choices
        
    Examples:
        >>> validate_choice("red", ["red", "green", "blue"])
        'red'
        >>> validate_choice("RED", ["red", "green", "blue"], case_sensitive=False)
        'red'
    """
    if not isinstance(choices, list) or len(choices) == 0:
        raise ValueError("Choices must be a non-empty list")
    
    # Case-insensitive comparison for strings
    if not case_sensitive and isinstance(value, str):
        value_lower = value.lower()
        for choice in choices:
            if isinstance(choice, str) and choice.lower() == value_lower:
                return choice
        # Not found
        raise ValidationError(
            f"Invalid {field_name}: '{value}'. Must be one of: {choices}",
            field=field_name
        )
    
    # Direct comparison
    if value in choices:
        return value
    
    raise ValidationError(
        f"Invalid {field_name}: '{value}'. Must be one of: {choices}",
        field=field_name
    )


# ============================================================================
# Helper Functions
# ============================================================================

def is_valid_ticker(ticker: str) -> bool:
    """
    Check if ticker is valid (without raising exception).
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        True if valid, False otherwise
    """
    try:
        validate_ticker(ticker)
        return True
    except TickerValidationError:
        return False


def is_valid_date(date_input: Union[str, date, datetime]) -> bool:
    """
    Check if date is valid (without raising exception).
    
    Args:
        date_input: Date input
        
    Returns:
        True if valid, False otherwise
    """
    try:
        validate_date(date_input)
        return True
    except DateValidationError:
        return False


def is_valid_email(email: str) -> bool:
    """
    Check if email is valid (without raising exception).
    
    Args:
        email: Email address
        
    Returns:
        True if valid, False otherwise
    """
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False
