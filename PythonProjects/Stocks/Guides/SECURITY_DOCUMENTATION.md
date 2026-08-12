# Security Documentation

**StockIQ Platform - Security Hardening Implementation**

## Overview

This document describes the comprehensive security measures implemented in the StockIQ platform to protect against common vulnerabilities and attacks. The implementation follows OWASP security best practices and industry standards for financial applications.

## Table of Contents

1. [API Key and Secret Protection](#api-key-and-secret-protection)
2. [Input Validation and Sanitization](#input-validation-and-sanitization)
3. [SQL Injection Prevention](#sql-injection-prevention)
4. [XSS Protection](#xss-protection)
5. [CSRF Protection](#csrf-protection)
6. [Rate Limiting](#rate-limiting)
7. [Security Headers](#security-headers)
8. [Security Logging and Monitoring](#security-logging-and-monitoring)
9. [Password Management](#password-management)
10. [Dependency Security](#dependency-security)
11. [Security Best Practices](#security-best-practices)

---

## API Key and Secret Protection

### Implementation

**Module:** `stockiq.infrastructure.security.APIKeyValidator`, `SecretManager`

### Features

1. **API Key Masking**: All API keys are masked in logs and error messages
   - Only first 4 and last 4 characters shown
   - Example: `sk_t...a8f3`

2. **API Key Detection**: Automatic detection of exposed keys in text/logs
   - Multiple pattern recognition
   - Alerts on potential leaks

3. **Secret Manager**: Centralized secret storage with rotation support
   - Metadata tracking (creation time, expiry)
   - Automatic expiry checking
   - Secret rotation with audit trail

### Usage

```python
from stockiq.infrastructure.security import api_key_validator, secret_manager

# Mask API key for logging
masked = api_key_validator.mask_api_key("sk_test_1234567890abcdef")
# Output: "sk_t...cdef"

# Store secret
secret_manager.store_secret(
    "newsapi_key",
    "your_actual_key_here",
    metadata={"expires_at": datetime.utcnow() + timedelta(days=90)}
)

# Retrieve secret
key = secret_manager.get_secret("newsapi_key")

# Rotate secret
secret_manager.rotate_secret("newsapi_key", "new_key_value")
```

### Environment Variables

All API keys and secrets MUST be stored in environment variables, never in code:

```bash
# .env file (NEVER commit to git)
NEWSAPI_KEY=your_key_here
FINNHUB_API_KEY=your_key_here
ALPHAVANTAGE_API_KEY=your_key_here
SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_here
```

### .gitignore Configuration

Ensure these files are excluded:

```
.env
.env.local
.env.*.local
*.key
*.pem
secrets/
```

---

## Input Validation and Sanitization

### Implementation

**Module:** `stockiq.infrastructure.security.InputValidator`

### Features

1. **Multi-Type Validation**: String, email, ticker, number, integer
2. **HTML Sanitization**: Removes dangerous HTML tags
3. **Length Enforcement**: Maximum length checks
4. **Injection Detection**: SQL, XSS, command injection detection

### Validation Functions

```python
from stockiq.infrastructure.security import input_validator

# Validate and sanitize string
is_valid, sanitized, error = input_validator.validate_and_sanitize(
    user_input,
    field_type="string",
    required=True,
    max_length=100
)

# Validate ticker
if input_validator.validate_ticker("AAPL"):
    # Valid ticker
    pass

# Validate email
if input_validator.validate_email("user@example.com"):
    # Valid email
    pass

# Detect SQL injection
if input_validator.detect_sql_injection(user_input):
    # Block request
    raise SecurityException("SQL injection detected")
```

### Supported Field Types

- `string`: General text with sanitization
- `ticker`: Stock ticker (1-5 uppercase letters)
- `email`: Email address validation
- `number`: Floating point numbers
- `integer`: Integer values

### Middleware Integration

Use the `secure_endpoint` decorator for automatic validation:

```python
from stockiq.infrastructure.security_middleware import secure_endpoint

@secure_endpoint(
    rate_limit_type="api",
    validate_inputs={"ticker": "ticker", "email": "email"}
)
def analyze_stock(ticker: str, email: str):
    # Inputs are automatically validated and sanitized
    pass
```

---

## SQL Injection Prevention

### Implementation

**Modules:** 
- `stockiq.infrastructure.database` (parameterized queries)
- `stockiq.infrastructure.security_middleware` (validation)

### Strategy: Defense in Depth

1. **Primary Defense**: Parameterized queries (SQLAlchemy)
2. **Secondary Defense**: Input validation
3. **Tertiary Defense**: Query pattern detection

### Parameterized Query Enforcement

**ALWAYS use parameterized queries:**

```python
from stockiq.infrastructure.database import execute_safe_query, get_db_context

# ✅ CORRECT: Parameterized query
with get_db_context() as db:
    result = execute_safe_query(
        db,
        "SELECT * FROM stocks WHERE ticker = :ticker AND sector = :sector",
        {"ticker": "AAPL", "sector": "Technology"}
    )

# ❌ WRONG: String concatenation (WILL RAISE ERROR)
query = f"SELECT * FROM stocks WHERE ticker = '{ticker}'"  # DANGEROUS!
```

### Safe Query Builder

For complex queries, use the safe query builder:

```python
from stockiq.infrastructure.database import build_safe_query

# Build safe SELECT query
query, params = build_safe_query(
    table_name="stocks",
    columns=["ticker", "price", "market_cap"],
    filters=[
        ("market_cap", ">", 1000000000),
        ("sector", "=", "Technology")
    ],
    order_by=[("market_cap", "DESC")],
    limit=10
)

# Execute safely
result = execute_safe_query(db, query, params)
```

### SQLAlchemy ORM (Recommended)

Using SQLAlchemy ORM automatically provides parameterization:

```python
from sqlalchemy import select
from stockiq.infrastructure.models import Stock

# ORM queries are automatically parameterized
stmt = select(Stock).where(
    Stock.ticker == ticker,  # Automatically parameterized
    Stock.market_cap > 1000000
)
result = session.execute(stmt).scalars().all()
```

---

## XSS Protection

### Implementation

**Modules:**
- `stockiq.infrastructure.security.InputValidator`
- `stockiq.infrastructure.security_middleware`

### Protection Layers

1. **Input Sanitization**: Remove dangerous HTML/JavaScript
2. **Output Encoding**: Escape HTML entities
3. **Content Security Policy**: Browser-level protection

### Input Sanitization

```python
from stockiq.infrastructure.security import input_validator

# Sanitize user input
clean_text = input_validator.sanitize_string(user_input)

# Detect XSS attempts
if input_validator.detect_xss(user_input):
    # Block and log
    raise XSSException("XSS attempt detected")
```

### Output Sanitization (HTML)

```python
from stockiq.infrastructure.security_middleware import sanitize_html_output

# Sanitize HTML before rendering
safe_html = sanitize_html_output(user_generated_html)
```

### Streamlit-Specific Protection

Streamlit automatically escapes output, but for HTML rendering:

```python
import streamlit as st
from stockiq.infrastructure.security_middleware import sanitize_html_output

# Sanitize before rendering HTML
safe_html = sanitize_html_output(user_html)
st.markdown(safe_html, unsafe_allow_html=True)
```

### Content Security Policy

CSP headers are automatically applied. See [Security Headers](#security-headers) section.

---

## CSRF Protection

### Implementation

**Module:** `stockiq.infrastructure.security.CSRFProtection`

### Token-Based Protection

CSRF tokens are required for all state-changing operations.

### Usage in Streamlit

```python
from stockiq.infrastructure.security_middleware import (
    init_session_security,
    secure_endpoint
)
import streamlit as st

# Initialize security (call once per session)
init_session_security()

# Protected endpoint
@secure_endpoint(require_csrf=True)
def update_watchlist(ticker: str):
    # This function requires valid CSRF token
    pass

# Get CSRF token for forms
csrf_token = st.session_state.csrf_token
```

### Token Lifecycle

- **Generation**: Automatic on session creation
- **Expiry**: 1 hour (configurable)
- **Validation**: Automatic in `@secure_endpoint` decorator
- **Cleanup**: Automatic removal of expired tokens

### Manual CSRF Validation

```python
from stockiq.infrastructure.security import CSRFProtection
from stockiq.infrastructure.config import get_settings

csrf = CSRFProtection(get_settings().secret_key)

# Generate token
token = csrf.generate_token(session_id="user_123")

# Validate token
if csrf.validate_token(session_id="user_123", token_with_sig=token):
    # Token is valid
    pass
```

---

## Rate Limiting

### Implementation

**Module:** `stockiq.infrastructure.security.RateLimiter`

### Token Bucket Algorithm

Uses token bucket algorithm with per-client tracking for fair and efficient rate limiting.

### Pre-configured Limiters

1. **API Limiter**: 100 requests/minute (burst: 120)
2. **Search Limiter**: 20 requests/minute (burst: 25)
3. **Heavy Limiter**: 10 requests/minute (burst: 12)
   - Used for ML predictions, backtests, heavy computations

### Usage with Decorator

```python
from stockiq.infrastructure.security_middleware import secure_endpoint

@secure_endpoint(rate_limit_type="api")
def get_stock_data(ticker: str):
    # Rate limited to 100 req/min
    pass

@secure_endpoint(rate_limit_type="heavy")
def run_backtest(strategy: str):
    # Rate limited to 10 req/min
    pass
```

### Manual Rate Limiting

```python
from stockiq.infrastructure.security import RateLimiter

# Create custom rate limiter
limiter = RateLimiter(
    max_requests=50,   # 50 requests
    time_window=60,    # per minute
    burst_size=60      # allow burst of 60
)

# Check rate limit
allowed, metadata = limiter.allow_request(client_id="user_123")

if not allowed:
    print(f"Rate limit exceeded. Retry after {metadata['retry_after']}s")
else:
    # Process request
    pass
```

### Rate Limit Headers

Rate limit metadata is available in responses:

```json
{
  "remaining": 45,
  "limit": 100,
  "reset_at": 1234567890,
  "retry_after": 0
}
```

---

## Security Headers

### Implementation

**Module:** `stockiq.infrastructure.security.SecurityHeaders`

### Applied Headers

All HTTP responses include these security headers:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-XSS-Protection` | `1; mode=block` | Enable XSS filter (legacy browsers) |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `Content-Security-Policy` | See below | Control resource loading |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer info |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Disable unnecessary features |

### Content Security Policy

Default CSP policy:

```
default-src 'self';
script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.plot.ly;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' https://fonts.gstatic.com;
img-src 'self' data: https:;
connect-src 'self' https://api.polygon.io https://finnhub.io;
frame-ancestors 'none';
base-uri 'self';
form-action 'self'
```

### Usage

Headers are automatically applied by middleware. To customize:

```python
from stockiq.infrastructure.security import SecurityHeaders

headers = SecurityHeaders.get_headers(
    csp_policy="your-custom-csp",
    frame_options="SAMEORIGIN",
    hsts_max_age=63072000  # 2 years
)
```

---

## Security Logging and Monitoring

### Implementation

**Module:** `stockiq.infrastructure.security.SecurityMonitor`

### Logged Events

All security-relevant events are logged with structured logging:

1. **Authentication Events**
   - Login attempts (success/failure)
   - Session creation/destruction
   - Token generation/validation

2. **Authorization Events**
   - Access granted/denied
   - Permission checks

3. **Input Validation Events**
   - Validation failures
   - Injection attempts detected

4. **Rate Limiting Events**
   - Rate limit exceeded
   - Client blocked/unblocked

5. **Security Violations**
   - CSRF token validation failures
   - SQL injection attempts
   - XSS attempts
   - Command injection attempts

### Usage

```python
from stockiq.infrastructure.security import security_monitor

# Log authentication attempt
security_monitor.log_authentication_attempt(
    success=True,
    client_id="user_123",
    method="api_key",
    details={"ip": "192.168.1.1"}
)

# Log authorization check
security_monitor.log_authorization_check(
    allowed=True,
    client_id="user_123",
    resource="stock_data",
    action="read"
)

# Log data access
security_monitor.log_data_access(
    client_id="user_123",
    resource="price_data",
    action="query",
    record_count=100
)

# Get event statistics
counts = security_monitor.get_event_counts()
```

### Log Format

Structured JSON logs for easy parsing and analysis:

```json
{
  "event": "auth_failure",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "client_id": "user_123",
  "details": {
    "method": "password",
    "ip": "192.168.1.1",
    "reason": "invalid_credentials"
  },
  "count": 3
}
```

### Monitoring Alerts

Configure alerts for critical security events:

1. **Multiple Failed Logins**: 5+ failures in 5 minutes
2. **SQL Injection Attempts**: Any detection
3. **Rate Limit Abuse**: Excessive 429 responses
4. **Unauthorized Access**: 403 responses

---

## Password Management

### Implementation

**Module:** `stockiq.infrastructure.security`

### Features

1. **Secure Hashing**: PBKDF2-HMAC-SHA256 with 100k iterations
2. **Random Salts**: Unique salt per password
3. **Constant-Time Comparison**: Prevents timing attacks

### Usage

```python
from stockiq.infrastructure.security import hash_password, verify_password

# Hash password
hashed, salt = hash_password("user_password")

# Store hashed and salt in database
# ...

# Verify password
if verify_password("user_password", hashed, salt):
    # Password correct
    pass
```

### Password Requirements

Enforce strong passwords:

- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character
- No common passwords (dictionary check)

---

## Dependency Security

### Vulnerability Scanning

Regularly scan dependencies for known vulnerabilities:

```bash
# Install safety
pip install safety

# Scan dependencies
safety check

# Or use pip-audit
pip install pip-audit
pip-audit
```

### Update Strategy

1. **Regular Updates**: Update dependencies monthly
2. **Security Patches**: Apply critical patches immediately
3. **Testing**: Test updates in staging before production
4. **Pinning**: Use exact versions in production

### Dependency Monitoring

Configure automated dependency monitoring:

- **GitHub Dependabot**: Automatic PR for updates
- **Snyk**: Real-time vulnerability monitoring
- **OWASP Dependency Check**: CI/CD integration

---

## Security Best Practices

### Development

1. **Never commit secrets**: Use environment variables
2. **Code reviews**: Require security review for sensitive code
3. **Static analysis**: Use tools like Bandit, semgrep
4. **Dependency scanning**: Automate vulnerability checks

### Deployment

1. **HTTPS Only**: Enforce TLS 1.2+ in production
2. **Environment Isolation**: Separate dev/staging/prod
3. **Least Privilege**: Minimize service permissions
4. **Regular Backups**: Automated encrypted backups
5. **Monitoring**: Real-time security event monitoring

### Operations

1. **Incident Response**: Document procedures
2. **Security Updates**: Apply patches promptly
3. **Access Logs**: Retain for audit (90 days minimum)
4. **Penetration Testing**: Annual security audits

### Compliance

For institutional use, ensure compliance with:

- **SOC 2**: Security controls documentation
- **PCI DSS**: If handling payment data
- **GDPR**: If handling EU user data
- **FINRA**: Financial industry regulations

---

## Security Checklist

### Before Production

- [ ] All secrets in environment variables
- [ ] `.env` file in `.gitignore`
- [ ] HTTPS configured with valid certificate
- [ ] Security headers enabled
- [ ] Rate limiting configured
- [ ] CSRF protection enabled
- [ ] Input validation on all endpoints
- [ ] Parameterized queries enforced
- [ ] Error messages don't leak sensitive info
- [ ] Logging configured for security events
- [ ] Dependency vulnerabilities resolved
- [ ] Security testing completed
- [ ] Incident response plan documented
- [ ] Backup and recovery tested

### Regular Maintenance

- [ ] Update dependencies monthly
- [ ] Review security logs weekly
- [ ] Rotate API keys quarterly
- [ ] Review access logs monthly
- [ ] Test backups monthly
- [ ] Security audit annually
- [ ] Update security documentation quarterly

---

## Security Contact

For security issues or vulnerabilities:

- **Email**: security@stockiq.example.com
- **Responsible Disclosure**: 90-day disclosure policy
- **Acknowledgments**: Security researchers credited

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CWE Top 25](https://cwe.mitre.org/top25/)

---

**Last Updated**: January 2024
**Version**: 1.0
**Status**: Production Ready
