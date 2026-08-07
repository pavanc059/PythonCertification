"""
Security hardening module for the StockIQ application.

This module implements comprehensive security measures including:
- API key and secret protection
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CSRF protection
- Rate limiting
- Security headers
- Security logging and monitoring
"""

import os
import re
import secrets
import hashlib
import hmac
import time
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
import logging
from collections import defaultdict
from threading import Lock

import structlog
from pydantic import BaseModel, validator, Field
import bleach

# Configure structured logging for security events
security_logger = structlog.get_logger("security")


# ============================================================================
# API Key and Secret Protection
# ============================================================================

class APIKeyValidator:
    """Validates and masks API keys for secure handling."""
    
    # Patterns for detecting API keys
    API_KEY_PATTERNS = {
        'generic': re.compile(r'(?i)(api[_-]?key|apikey|api[_-]?secret)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})'),
        'bearer': re.compile(r'Bearer\s+([a-zA-Z0-9_\-\.]+)'),
        'basic': re.compile(r'Basic\s+([a-zA-Z0-9+/=]+)'),
    }
    
    @staticmethod
    def mask_api_key(key: str) -> str:
        """
        Mask an API key for logging/display purposes.
        
        Args:
            key: The API key to mask
            
        Returns:
            Masked API key showing only first 4 and last 4 characters
        """
        if not key or len(key) < 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"
    
    @staticmethod
    def validate_api_key_format(key: str, min_length: int = 20) -> bool:
        """
        Validate API key format (length and character set).
        
        Args:
            key: The API key to validate
            min_length: Minimum required length
            
        Returns:
            True if valid format, False otherwise
        """
        if not key or len(key) < min_length:
            return False
        # Check for reasonable character set (alphanumeric + common special chars)
        return bool(re.match(r'^[a-zA-Z0-9_\-\.]+$', key))
    
    @staticmethod
    def detect_exposed_keys(text: str) -> List[str]:
        """
        Detect potentially exposed API keys in text.
        
        Args:
            text: Text to scan for API keys
            
        Returns:
            List of detected key patterns (masked)
        """
        detected = []
        for pattern_name, pattern in APIKeyValidator.API_KEY_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                for match in matches:
                    key = match if isinstance(match, str) else match[1]
                    detected.append(f"{pattern_name}: {APIKeyValidator.mask_api_key(key)}")
        return detected


class SecretManager:
    """Manages secrets and API keys with secure storage and rotation support."""
    
    def __init__(self):
        self._secrets_cache: Dict[str, Dict[str, Any]] = {}
        self._rotation_timestamps: Dict[str, datetime] = {}
    
    def store_secret(self, name: str, value: str, metadata: Optional[Dict] = None) -> None:
        """
        Store a secret with metadata.
        
        Args:
            name: Secret identifier
            value: Secret value
            metadata: Optional metadata (expiry, rotation schedule, etc.)
        """
        self._secrets_cache[name] = {
            'value': value,
            'stored_at': datetime.utcnow(),
            'metadata': metadata or {}
        }
        security_logger.info(
            "secret_stored",
            secret_name=name,
            has_metadata=bool(metadata)
        )
    
    def get_secret(self, name: str) -> Optional[str]:
        """
        Retrieve a secret by name.
        
        Args:
            name: Secret identifier
            
        Returns:
            Secret value or None if not found
        """
        secret_data = self._secrets_cache.get(name)
        if secret_data:
            # Check expiry if set
            metadata = secret_data.get('metadata', {})
            if 'expires_at' in metadata:
                if datetime.utcnow() > metadata['expires_at']:
                    security_logger.warning("secret_expired", secret_name=name)
                    return None
            return secret_data['value']
        return None
    
    def rotate_secret(self, name: str, new_value: str) -> None:
        """
        Rotate a secret with a new value.
        
        Args:
            name: Secret identifier
            new_value: New secret value
        """
        if name in self._secrets_cache:
            self._rotation_timestamps[name] = datetime.utcnow()
            self._secrets_cache[name]['value'] = new_value
            self._secrets_cache[name]['rotated_at'] = datetime.utcnow()
            security_logger.info("secret_rotated", secret_name=name)
        else:
            security_logger.error("secret_not_found", secret_name=name)


# ============================================================================
# Input Validation and Sanitization
# ============================================================================

class InputValidator:
    """Validates and sanitizes user inputs to prevent injection attacks."""
    
    # Allowed HTML tags for rich text (empty = strip all HTML)
    ALLOWED_TAGS = []
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)", re.IGNORECASE),
        re.compile(r"(--|#|/\*|\*/|;|\bOR\b|\bAND\b).*(\=|LIKE)", re.IGNORECASE),
        re.compile(r"(\bunion\b.*\bselect\b)", re.IGNORECASE),
        re.compile(r"(\bxp_cmdshell\b)", re.IGNORECASE),
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),  # Event handlers
        re.compile(r"<iframe", re.IGNORECASE),
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        re.compile(r"[;&|`$()]"),
        re.compile(r"\b(rm|cat|wget|curl|chmod|chown)\b"),
    ]
    
    @staticmethod
    def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize a string input by removing HTML and trimming.
        
        Args:
            value: Input string
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
        """
        # Remove HTML tags
        sanitized = bleach.clean(value, tags=InputValidator.ALLOWED_TAGS, strip=True)
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        # Enforce max length
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
    
    @staticmethod
    def validate_ticker(ticker: str) -> bool:
        """
        Validate stock ticker format.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            True if valid, False otherwise
        """
        # Tickers: 1-5 uppercase letters, optionally followed by .letter for exchanges
        return bool(re.match(r'^[A-Z]{1,5}(\.[A-Z])?$', ticker))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email address format.
        
        Args:
            email: Email address
            
        Returns:
            True if valid, False otherwise
        """
        pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return bool(pattern.match(email))
    
    @staticmethod
    def detect_sql_injection(value: str) -> bool:
        """
        Detect potential SQL injection attempts.
        
        Args:
            value: Input string to check
            
        Returns:
            True if SQL injection detected, False otherwise
        """
        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            if pattern.search(value):
                security_logger.warning(
                    "sql_injection_detected",
                    value=value[:100],  # Log only first 100 chars
                    pattern=pattern.pattern
                )
                return True
        return False
    
    @staticmethod
    def detect_xss(value: str) -> bool:
        """
        Detect potential XSS attacks.
        
        Args:
            value: Input string to check
            
        Returns:
            True if XSS detected, False otherwise
        """
        for pattern in InputValidator.XSS_PATTERNS:
            if pattern.search(value):
                security_logger.warning(
                    "xss_attempt_detected",
                    value=value[:100]
                )
                return True
        return False
    
    @staticmethod
    def detect_command_injection(value: str) -> bool:
        """
        Detect potential command injection attempts.
        
        Args:
            value: Input string to check
            
        Returns:
            True if command injection detected, False otherwise
        """
        for pattern in InputValidator.COMMAND_INJECTION_PATTERNS:
            if pattern.search(value):
                security_logger.warning(
                    "command_injection_detected",
                    value=value[:100]
                )
                return True
        return False
    
    @staticmethod
    def validate_and_sanitize(
        value: Any,
        field_type: str,
        required: bool = True,
        max_length: Optional[int] = None
    ) -> tuple[bool, Any, Optional[str]]:
        """
        Comprehensive validation and sanitization.
        
        Args:
            value: Input value
            field_type: Type of field (string, email, ticker, number, etc.)
            required: Whether field is required
            max_length: Maximum length for strings
            
        Returns:
            Tuple of (is_valid, sanitized_value, error_message)
        """
        # Check required
        if value is None or value == "":
            if required:
                return False, None, "Field is required"
            return True, None, None
        
        # Type-specific validation
        if field_type == "string":
            if not isinstance(value, str):
                return False, None, "Must be a string"
            # Check for injection attacks
            if InputValidator.detect_sql_injection(value):
                return False, None, "Invalid input: potential SQL injection"
            if InputValidator.detect_xss(value):
                return False, None, "Invalid input: potential XSS"
            if InputValidator.detect_command_injection(value):
                return False, None, "Invalid input: potential command injection"
            # Sanitize
            sanitized = InputValidator.sanitize_string(value, max_length)
            return True, sanitized, None
        
        elif field_type == "ticker":
            if not isinstance(value, str):
                return False, None, "Ticker must be a string"
            ticker = value.upper().strip()
            if not InputValidator.validate_ticker(ticker):
                return False, None, "Invalid ticker format"
            return True, ticker, None
        
        elif field_type == "email":
            if not isinstance(value, str):
                return False, None, "Email must be a string"
            email = value.lower().strip()
            if not InputValidator.validate_email(email):
                return False, None, "Invalid email format"
            return True, email, None
        
        elif field_type == "number":
            try:
                num = float(value)
                return True, num, None
            except (ValueError, TypeError):
                return False, None, "Must be a number"
        
        elif field_type == "integer":
            try:
                num = int(value)
                return True, num, None
            except (ValueError, TypeError):
                return False, None, "Must be an integer"
        
        else:
            return False, None, f"Unknown field type: {field_type}"


# ============================================================================
# CSRF Protection
# ============================================================================

class CSRFProtection:
    """CSRF token generation and validation."""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
    
    def generate_token(self, session_id: str, expires_in: int = 3600) -> str:
        """
        Generate a CSRF token for a session.
        
        Args:
            session_id: Session identifier
            expires_in: Token expiry in seconds (default 1 hour)
            
        Returns:
            CSRF token
        """
        # Generate random token
        token = secrets.token_urlsafe(32)
        
        # Create HMAC signature
        signature = hmac.new(
            self.secret_key.encode(),
            f"{session_id}:{token}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Store token with expiry
        with self._lock:
            self._tokens[token] = {
                'session_id': session_id,
                'signature': signature,
                'expires_at': datetime.utcnow() + timedelta(seconds=expires_in)
            }
        
        return f"{token}:{signature}"
    
    def validate_token(self, session_id: str, token_with_sig: str) -> bool:
        """
        Validate a CSRF token.
        
        Args:
            session_id: Session identifier
            token_with_sig: Token with signature (token:signature)
            
        Returns:
            True if valid, False otherwise
        """
        try:
            token, provided_sig = token_with_sig.split(':', 1)
        except ValueError:
            security_logger.warning("csrf_invalid_format", session_id=session_id)
            return False
        
        with self._lock:
            token_data = self._tokens.get(token)
            
            if not token_data:
                security_logger.warning("csrf_token_not_found", session_id=session_id)
                return False
            
            # Check expiry
            if datetime.utcnow() > token_data['expires_at']:
                security_logger.warning("csrf_token_expired", session_id=session_id)
                del self._tokens[token]
                return False
            
            # Check session
            if token_data['session_id'] != session_id:
                security_logger.warning("csrf_session_mismatch", session_id=session_id)
                return False
            
            # Check signature
            expected_sig = token_data['signature']
            if not hmac.compare_digest(provided_sig, expected_sig):
                security_logger.warning("csrf_signature_invalid", session_id=session_id)
                return False
            
            return True
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired tokens.
        
        Returns:
            Number of tokens removed
        """
        now = datetime.utcnow()
        with self._lock:
            expired = [
                token for token, data in self._tokens.items()
                if now > data['expires_at']
            ]
            for token in expired:
                del self._tokens[token]
        return len(expired)


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """
    Token bucket rate limiter with per-client tracking.
    """
    
    def __init__(
        self,
        max_requests: int,
        time_window: int,
        burst_size: Optional[int] = None
    ):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
            burst_size: Maximum burst size (default: max_requests)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.burst_size = burst_size or max_requests
        
        # Track requests per client
        self._buckets: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                'tokens': self.burst_size,
                'last_update': time.time()
            }
        )
        self._lock = Lock()
    
    def _refill_bucket(self, bucket: Dict[str, Any]) -> None:
        """Refill bucket based on time elapsed."""
        now = time.time()
        elapsed = now - bucket['last_update']
        
        # Calculate tokens to add based on rate
        tokens_to_add = (elapsed / self.time_window) * self.max_requests
        
        bucket['tokens'] = min(
            self.burst_size,
            bucket['tokens'] + tokens_to_add
        )
        bucket['last_update'] = now
    
    def allow_request(self, client_id: str) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request should be allowed for client.
        
        Args:
            client_id: Client identifier (IP, user_id, API key, etc.)
            
        Returns:
            Tuple of (allowed, metadata)
            metadata includes: remaining, reset_at, retry_after
        """
        with self._lock:
            bucket = self._buckets[client_id]
            self._refill_bucket(bucket)
            
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                allowed = True
                retry_after = 0
            else:
                allowed = False
                # Calculate retry after (time until next token)
                retry_after = max(0, self.time_window / self.max_requests)
            
            metadata = {
                'remaining': int(bucket['tokens']),
                'limit': self.max_requests,
                'reset_at': bucket['last_update'] + self.time_window,
                'retry_after': retry_after
            }
            
            if not allowed:
                security_logger.warning(
                    "rate_limit_exceeded",
                    client_id=client_id,
                    metadata=metadata
                )
            
            return allowed, metadata
    
    def reset_client(self, client_id: str) -> None:
        """Reset rate limit for a specific client."""
        with self._lock:
            if client_id in self._buckets:
                del self._buckets[client_id]


def rate_limit(
    limiter: RateLimiter,
    get_client_id: Callable[[], str]
) -> Callable:
    """
    Decorator for rate limiting function calls.
    
    Args:
        limiter: RateLimiter instance
        get_client_id: Function to get client identifier
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            client_id = get_client_id()
            allowed, metadata = limiter.allow_request(client_id)
            
            if not allowed:
                raise RateLimitExceeded(
                    f"Rate limit exceeded. Retry after {metadata['retry_after']:.2f} seconds",
                    metadata=metadata
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str, metadata: Dict[str, Any]):
        super().__init__(message)
        self.metadata = metadata


# ============================================================================
# Security Headers
# ============================================================================

class SecurityHeaders:
    """Security headers for HTTP responses."""
    
    @staticmethod
    def get_headers(
        csp_policy: Optional[str] = None,
        frame_options: str = "DENY",
        hsts_max_age: int = 31536000
    ) -> Dict[str, str]:
        """
        Get recommended security headers.
        
        Args:
            csp_policy: Content Security Policy (default: strict)
            frame_options: X-Frame-Options value (DENY, SAMEORIGIN, ALLOW-FROM)
            hsts_max_age: HSTS max age in seconds (default: 1 year)
            
        Returns:
            Dictionary of security headers
        """
        # Default strict CSP
        if csp_policy is None:
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.plot.ly; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://api.polygon.io https://finnhub.io; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        
        headers = {
            # Prevent MIME sniffing
            'X-Content-Type-Options': 'nosniff',
            
            # XSS Protection (legacy browsers)
            'X-XSS-Protection': '1; mode=block',
            
            # Frame Options
            'X-Frame-Options': frame_options,
            
            # Content Security Policy
            'Content-Security-Policy': csp_policy,
            
            # HSTS (HTTPS enforcement)
            'Strict-Transport-Security': f'max-age={hsts_max_age}; includeSubDomains',
            
            # Referrer Policy
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            
            # Permissions Policy (formerly Feature Policy)
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        }
        
        return headers


# ============================================================================
# Security Logging and Monitoring
# ============================================================================

class SecurityMonitor:
    """Monitor and log security events."""
    
    def __init__(self):
        self.logger = security_logger
        self._event_counts: Dict[str, int] = defaultdict(int)
        self._lock = Lock()
    
    def log_event(
        self,
        event_type: str,
        severity: str,
        details: Dict[str, Any],
        client_id: Optional[str] = None
    ) -> None:
        """
        Log a security event.
        
        Args:
            event_type: Type of security event
            severity: Severity level (info, warning, error, critical)
            details: Event details
            client_id: Optional client identifier
        """
        with self._lock:
            self._event_counts[event_type] += 1
        
        log_method = getattr(self.logger, severity, self.logger.info)
        log_method(
            event_type,
            client_id=client_id,
            details=details,
            count=self._event_counts[event_type]
        )
    
    def get_event_counts(self) -> Dict[str, int]:
        """Get counts of security events by type."""
        with self._lock:
            return dict(self._event_counts)
    
    def log_authentication_attempt(
        self,
        success: bool,
        client_id: str,
        method: str,
        details: Optional[Dict] = None
    ) -> None:
        """Log an authentication attempt."""
        event_type = "auth_success" if success else "auth_failure"
        severity = "info" if success else "warning"
        
        self.log_event(
            event_type,
            severity,
            {
                'method': method,
                'timestamp': datetime.utcnow().isoformat(),
                **(details or {})
            },
            client_id=client_id
        )
    
    def log_authorization_check(
        self,
        allowed: bool,
        client_id: str,
        resource: str,
        action: str
    ) -> None:
        """Log an authorization check."""
        event_type = "authz_allowed" if allowed else "authz_denied"
        severity = "info" if allowed else "warning"
        
        self.log_event(
            event_type,
            severity,
            {
                'resource': resource,
                'action': action,
                'timestamp': datetime.utcnow().isoformat()
            },
            client_id=client_id
        )
    
    def log_data_access(
        self,
        client_id: str,
        resource: str,
        action: str,
        record_count: int = 1
    ) -> None:
        """Log data access for audit trail."""
        self.log_event(
            "data_access",
            "info",
            {
                'resource': resource,
                'action': action,
                'record_count': record_count,
                'timestamp': datetime.utcnow().isoformat()
            },
            client_id=client_id
        )


# ============================================================================
# Global Instances
# ============================================================================

# Create global instances for easy access
api_key_validator = APIKeyValidator()
secret_manager = SecretManager()
input_validator = InputValidator()
security_monitor = SecurityMonitor()


# ============================================================================
# Utility Functions
# ============================================================================

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Token length in bytes
        
    Returns:
        URL-safe base64 encoded token
    """
    return secrets.token_urlsafe(length)


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
    """
    Hash a password using PBKDF2-HMAC-SHA256.
    
    Args:
        password: Password to hash
        salt: Optional salt (generated if not provided)
        
    Returns:
        Tuple of (hashed_password_hex, salt_hex)
    """
    if salt is None:
        salt = secrets.token_bytes(32)
    
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000  # 100k iterations
    )
    
    return hashed.hex(), salt.hex()


def verify_password(password: str, hashed_hex: str, salt_hex: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        password: Password to verify
        hashed_hex: Hex-encoded hash
        salt_hex: Hex-encoded salt
        
    Returns:
        True if password matches, False otherwise
    """
    salt = bytes.fromhex(salt_hex)
    expected_hash = bytes.fromhex(hashed_hex)
    
    actual_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    
    return hmac.compare_digest(actual_hash, expected_hash)
