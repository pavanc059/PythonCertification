"""
Security middleware for Streamlit and Flask applications.

This module provides security middleware layers for:
- Request validation
- CSRF protection
- Rate limiting
- Security headers
- Input sanitization
- SQL injection prevention
"""

from typing import Optional, Dict, Any, Callable
from functools import wraps
import hashlib
from datetime import datetime

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

from .security import (
    InputValidator,
    CSRFProtection,
    RateLimiter,
    SecurityHeaders,
    security_monitor,
    RateLimitExceeded
)
from .config import get_settings


class StreamlitSecurityMiddleware:
    """Security middleware for Streamlit applications."""
    
    def __init__(self):
        self.settings = get_settings()
        self.csrf = CSRFProtection(self.settings.secret_key)
        self.headers = SecurityHeaders()
        
        # Create rate limiters for different endpoints
        self.api_limiter = RateLimiter(
            max_requests=100,  # 100 requests
            time_window=60,    # per minute
            burst_size=120
        )
        
        self.search_limiter = RateLimiter(
            max_requests=20,   # 20 searches
            time_window=60,    # per minute
            burst_size=25
        )
        
        self.heavy_limiter = RateLimiter(
            max_requests=10,   # 10 requests
            time_window=60,    # per minute (for ML predictions, backtests)
            burst_size=12
        )
    
    def get_client_id(self) -> str:
        """Get unique client identifier from session."""
        if STREAMLIT_AVAILABLE and hasattr(st, 'session_state'):
            # Use session ID or generate one
            if 'client_id' not in st.session_state:
                # In production, use proper session management
                # For now, generate based on session data
                st.session_state.client_id = hashlib.sha256(
                    str(id(st.session_state)).encode()
                ).hexdigest()[:16]
            return st.session_state.client_id
        return "default_client"
    
    def validate_input(
        self,
        value: Any,
        field_type: str,
        required: bool = True,
        max_length: Optional[int] = None
    ) -> tuple[bool, Any, Optional[str]]:
        """
        Validate and sanitize input with security monitoring.
        
        Args:
            value: Input value
            field_type: Field type (string, ticker, email, etc.)
            required: Whether field is required
            max_length: Maximum length for strings
            
        Returns:
            Tuple of (is_valid, sanitized_value, error_message)
        """
        is_valid, sanitized, error = InputValidator.validate_and_sanitize(
            value, field_type, required, max_length
        )
        
        if not is_valid:
            security_monitor.log_event(
                "input_validation_failed",
                "warning",
                {
                    'field_type': field_type,
                    'error': error,
                    'value_type': type(value).__name__
                },
                client_id=self.get_client_id()
            )
        
        return is_valid, sanitized, error
    
    def rate_limit(
        self,
        limiter_type: str = "api"
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check rate limit for current client.
        
        Args:
            limiter_type: Type of limiter (api, search, heavy)
            
        Returns:
            Tuple of (allowed, metadata)
        """
        # Select appropriate limiter
        if limiter_type == "search":
            limiter = self.search_limiter
        elif limiter_type == "heavy":
            limiter = self.heavy_limiter
        else:
            limiter = self.api_limiter
        
        client_id = self.get_client_id()
        allowed, metadata = limiter.allow_request(client_id)
        
        return allowed, metadata
    
    def check_csrf(self, token: str) -> bool:
        """
        Validate CSRF token for current session.
        
        Args:
            token: CSRF token to validate
            
        Returns:
            True if valid, False otherwise
        """
        client_id = self.get_client_id()
        return self.csrf.validate_token(client_id, token)
    
    def generate_csrf_token(self) -> str:
        """
        Generate CSRF token for current session.
        
        Returns:
            CSRF token
        """
        client_id = self.get_client_id()
        return self.csrf.generate_token(client_id)
    
    def apply_security_headers(self) -> Dict[str, str]:
        """
        Get security headers for response.
        
        Returns:
            Dictionary of security headers
        """
        return self.headers.get_headers()


def secure_endpoint(
    rate_limit_type: str = "api",
    require_csrf: bool = False,
    validate_inputs: Optional[Dict[str, str]] = None
):
    """
    Decorator to secure a function with middleware checks.
    
    Args:
        rate_limit_type: Type of rate limiter to apply
        require_csrf: Whether to require CSRF token
        validate_inputs: Dict mapping parameter names to field types
        
    Example:
        @secure_endpoint(rate_limit_type="heavy", validate_inputs={"ticker": "ticker"})
        def analyze_stock(ticker: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            middleware = StreamlitSecurityMiddleware()
            
            # Rate limiting
            allowed, metadata = middleware.rate_limit(rate_limit_type)
            if not allowed:
                raise RateLimitExceeded(
                    f"Rate limit exceeded. Try again in {metadata['retry_after']:.0f} seconds",
                    metadata=metadata
                )
            
            # CSRF check
            if require_csrf:
                if STREAMLIT_AVAILABLE and 'csrf_token' in st.session_state:
                    token = st.session_state.csrf_token
                    if not middleware.check_csrf(token):
                        raise SecurityException("Invalid CSRF token")
                else:
                    raise SecurityException("CSRF token required")
            
            # Input validation
            if validate_inputs:
                import inspect
                sig = inspect.signature(func)
                params = sig.parameters
                
                # Get bound arguments
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                
                # Validate each specified input
                for param_name, field_type in validate_inputs.items():
                    if param_name in bound.arguments:
                        value = bound.arguments[param_name]
                        is_valid, sanitized, error = middleware.validate_input(
                            value, field_type
                        )
                        if not is_valid:
                            raise ValidationException(f"Invalid {param_name}: {error}")
                        # Replace with sanitized value
                        bound.arguments[param_name] = sanitized
                
                # Call function with sanitized arguments
                return func(*bound.args, **bound.kwargs)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


class SecurityException(Exception):
    """Base exception for security violations."""
    pass


class ValidationException(SecurityException):
    """Exception for validation failures."""
    pass


class SQLInjectionException(SecurityException):
    """Exception for SQL injection attempts."""
    pass


class XSSException(SecurityException):
    """Exception for XSS attempts."""
    pass


def validate_sql_query_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate SQL query parameters to prevent SQL injection.
    
    This is used alongside parameterized queries as defense-in-depth.
    
    Args:
        params: Query parameters dictionary
        
    Returns:
        Validated parameters
        
    Raises:
        SQLInjectionException: If SQL injection detected
    """
    validated = {}
    
    for key, value in params.items():
        if isinstance(value, str):
            # Check for SQL injection patterns
            if InputValidator.detect_sql_injection(value):
                security_monitor.log_event(
                    "sql_injection_attempt",
                    "critical",
                    {'parameter': key, 'value': value[:100]},
                    client_id="sql_params"
                )
                raise SQLInjectionException(
                    f"Potential SQL injection detected in parameter: {key}"
                )
            validated[key] = value
        else:
            validated[key] = value
    
    return validated


def sanitize_html_output(html: str) -> str:
    """
    Sanitize HTML output to prevent XSS.
    
    Args:
        html: HTML string
        
    Returns:
        Sanitized HTML
    """
    # Use bleach to clean HTML
    import bleach
    
    # Allow only safe tags
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'a', 'span', 'div', 'table', 'tr', 'td', 'th',
        'thead', 'tbody', 'pre', 'code'
    ]
    
    allowed_attrs = {
        'a': ['href', 'title'],
        'span': ['class'],
        'div': ['class'],
        'td': ['colspan', 'rowspan'],
        'th': ['colspan', 'rowspan']
    }
    
    return bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True
    )


def log_security_event(
    event_type: str,
    severity: str = "info",
    details: Optional[Dict[str, Any]] = None
):
    """
    Log a security event.
    
    Args:
        event_type: Type of event
        severity: Severity level (info, warning, error, critical)
        details: Additional details
    """
    middleware = StreamlitSecurityMiddleware()
    client_id = middleware.get_client_id()
    
    security_monitor.log_event(
        event_type,
        severity,
        details or {},
        client_id=client_id
    )


# ============================================================================
# Streamlit-Specific Security Utilities
# ============================================================================

if STREAMLIT_AVAILABLE:
    
    def init_session_security():
        """Initialize security features in Streamlit session."""
        if 'security_initialized' not in st.session_state:
            middleware = StreamlitSecurityMiddleware()
            
            # Generate CSRF token
            st.session_state.csrf_token = middleware.generate_csrf_token()
            
            # Track security events
            st.session_state.security_events = []
            
            # Initialize rate limit counters
            st.session_state.request_count = 0
            st.session_state.last_request_time = datetime.utcnow()
            
            st.session_state.security_initialized = True
    
    def display_rate_limit_warning(metadata: Dict[str, Any]):
        """Display rate limit warning in Streamlit."""
        st.warning(
            f"⚠️ Rate limit exceeded. "
            f"You have {metadata['remaining']} requests remaining. "
            f"Please wait {metadata['retry_after']:.0f} seconds before trying again."
        )
    
    def display_security_error(error: SecurityException):
        """Display security error in Streamlit."""
        st.error(f"🛡️ Security Error: {str(error)}")
        
        # Log to security monitor
        log_security_event(
            "security_error_displayed",
            "warning",
            {'error_type': type(error).__name__, 'message': str(error)}
        )
