"""
Secrets management and API key rotation for the StockIQ application.

This module provides:
- Secure API key storage and retrieval
- API key rotation with grace periods
- Environment variable integration
- Secrets validation and expiry tracking
- Audit logging for secret access

All secrets are stored in environment variables and never hardcoded.
"""

import os
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# Exceptions
# ============================================================================

class SecretNotFoundError(Exception):
    """Raised when a secret is not found."""
    pass


class SecretExpiredError(Exception):
    """Raised when a secret has expired."""
    pass


class SecretRotationError(Exception):
    """Raised when secret rotation fails."""
    pass


# ============================================================================
# Secret Manager
# ============================================================================

class SecretsManager:
    """
    Manages API keys and secrets with rotation support.
    
    Features:
    - Load secrets from environment variables
    - Support for multiple secret versions (active + old for grace period)
    - Automatic expiry tracking
    - Rotation scheduling
    - Audit logging
    """
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize secrets manager.
        
        Args:
            env_file: Path to .env file (optional)
        """
        self._secrets: Dict[str, Dict[str, Any]] = {}
        self._rotation_schedule: Dict[str, datetime] = {}
        self._access_log: List[Dict[str, Any]] = []
        
        # Load from environment
        if env_file:
            self._load_from_env_file(env_file)
        else:
            self._load_from_environment()
        
        logger.info("secrets_manager_initialized", secret_count=len(self._secrets))
    
    def _load_from_environment(self):
        """Load secrets from environment variables."""
        # Define expected secret names
        secret_names = [
            'NEWSAPI_API_KEY',
            'FINNHUB_API_KEY',
            'ALPHA_VANTAGE_API_KEY',
            'POLYGON_API_KEY',
            'ALPACA_API_KEY',
            'ALPACA_SECRET_KEY',
            'DATABASE_PASSWORD',
            'REDIS_PASSWORD',
            'SECRET_KEY',  # Application secret key
        ]
        
        for name in secret_names:
            value = os.getenv(name)
            if value:
                self._secrets[name] = {
                    'value': value,
                    'loaded_at': datetime.utcnow(),
                    'source': 'environment',
                    'version': 1,
                    'expires_at': None,
                }
                logger.debug("secret_loaded", name=name, source="environment")
    
    def _load_from_env_file(self, env_file: str):
        """
        Load secrets from .env file.
        
        Args:
            env_file: Path to .env file
        """
        env_path = Path(env_file)
        if not env_path.exists():
            logger.warning("env_file_not_found", path=env_file)
            return
        
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    # Store secret
                    if key and value:
                        self._secrets[key] = {
                            'value': value,
                            'loaded_at': datetime.utcnow(),
                            'source': 'file',
                            'version': 1,
                            'expires_at': None,
                        }
                        logger.debug("secret_loaded", name=key, source="file")
    
    def get_secret(self, name: str, allow_old: bool = False) -> str:
        """
        Get a secret value by name.
        
        Args:
            name: Secret name
            allow_old: Whether to allow old (rotated) secrets during grace period
            
        Returns:
            Secret value
            
        Raises:
            SecretNotFoundError: If secret not found
            SecretExpiredError: If secret has expired
            
        Examples:
            >>> manager = SecretsManager()
            >>> api_key = manager.get_secret('NEWSAPI_API_KEY')
        """
        if name not in self._secrets:
            logger.error("secret_not_found", name=name)
            raise SecretNotFoundError(f"Secret '{name}' not found")
        
        secret_data = self._secrets[name]
        
        # Check expiry
        if secret_data.get('expires_at'):
            if datetime.utcnow() > secret_data['expires_at']:
                # Check if there's a new version
                if allow_old and f"{name}_OLD" in self._secrets:
                    logger.warning(
                        "using_old_secret_version",
                        name=name,
                        reason="primary_expired"
                    )
                    return self._secrets[f"{name}_OLD"]['value']
                
                logger.error("secret_expired", name=name)
                raise SecretExpiredError(f"Secret '{name}' has expired")
        
        # Log access
        self._log_access(name, success=True)
        
        return secret_data['value']
    
    def set_secret(
        self,
        name: str,
        value: str,
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Set or update a secret.
        
        Args:
            name: Secret name
            value: Secret value
            expires_in_days: Optional expiry in days
            metadata: Optional metadata
            
        Examples:
            >>> manager.set_secret('NEW_API_KEY', 'secret_value', expires_in_days=90)
        """
        # Calculate expiry
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Get current version
        current_version = 1
        if name in self._secrets:
            current_version = self._secrets[name].get('version', 1) + 1
        
        # Store secret
        self._secrets[name] = {
            'value': value,
            'loaded_at': datetime.utcnow(),
            'source': 'manual',
            'version': current_version,
            'expires_at': expires_at,
            'metadata': metadata or {}
        }
        
        logger.info(
            "secret_set",
            name=name,
            version=current_version,
            has_expiry=expires_at is not None
        )
    
    def rotate_secret(
        self,
        name: str,
        new_value: str,
        grace_period_days: int = 7
    ):
        """
        Rotate a secret with grace period for old value.
        
        During the grace period, both old and new secrets are valid.
        This allows gradual migration without service disruption.
        
        Args:
            name: Secret name
            new_value: New secret value
            grace_period_days: Grace period for old secret (default 7 days)
            
        Raises:
            SecretNotFoundError: If secret doesn't exist
            
        Examples:
            >>> manager.rotate_secret('NEWSAPI_API_KEY', 'new_key_value', grace_period_days=7)
        """
        if name not in self._secrets:
            raise SecretNotFoundError(f"Cannot rotate non-existent secret: {name}")
        
        # Save old secret with grace period
        old_secret = self._secrets[name].copy()
        old_secret['expires_at'] = datetime.utcnow() + timedelta(days=grace_period_days)
        old_secret['rotated_at'] = datetime.utcnow()
        self._secrets[f"{name}_OLD"] = old_secret
        
        # Set new secret
        new_version = old_secret.get('version', 1) + 1
        self._secrets[name] = {
            'value': new_value,
            'loaded_at': datetime.utcnow(),
            'source': 'rotation',
            'version': new_version,
            'expires_at': None,  # New secrets don't expire immediately
            'previous_version': old_secret.get('version'),
        }
        
        # Schedule rotation reminder
        next_rotation = datetime.utcnow() + timedelta(days=90)  # 90 days
        self._rotation_schedule[name] = next_rotation
        
        logger.info(
            "secret_rotated",
            name=name,
            new_version=new_version,
            grace_period_days=grace_period_days,
            next_rotation=next_rotation.isoformat()
        )
    
    def validate_secret(self, name: str, value: str) -> bool:
        """
        Validate a secret value against stored value.
        
        Args:
            name: Secret name
            value: Value to validate
            
        Returns:
            True if valid, False otherwise
            
        Examples:
            >>> is_valid = manager.validate_secret('NEWSAPI_API_KEY', 'test_key')
        """
        try:
            stored_value = self.get_secret(name, allow_old=True)
            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(stored_value, value)
        except (SecretNotFoundError, SecretExpiredError):
            return False
    
    def mask_secret(self, value: str, show_chars: int = 4) -> str:
        """
        Mask a secret for logging/display.
        
        Args:
            value: Secret value
            show_chars: Number of characters to show at start and end
            
        Returns:
            Masked secret
            
        Examples:
            >>> manager.mask_secret('secret_key_12345')
            'secr...2345'
        """
        if not value or len(value) <= show_chars * 2:
            return "***"
        
        return f"{value[:show_chars]}...{value[-show_chars:]}"
    
    def get_secret_metadata(self, name: str) -> Dict[str, Any]:
        """
        Get metadata for a secret.
        
        Args:
            name: Secret name
            
        Returns:
            Dictionary with metadata
            
        Raises:
            SecretNotFoundError: If secret not found
        """
        if name not in self._secrets:
            raise SecretNotFoundError(f"Secret '{name}' not found")
        
        secret_data = self._secrets[name]
        
        return {
            'name': name,
            'loaded_at': secret_data['loaded_at'].isoformat(),
            'source': secret_data['source'],
            'version': secret_data['version'],
            'expires_at': secret_data['expires_at'].isoformat() if secret_data.get('expires_at') else None,
            'is_expired': self._is_expired(name),
            'has_old_version': f"{name}_OLD" in self._secrets,
            'next_rotation': self._rotation_schedule.get(name).isoformat() if name in self._rotation_schedule else None,
        }
    
    def list_secrets(self, include_expired: bool = False) -> List[str]:
        """
        List all secret names.
        
        Args:
            include_expired: Whether to include expired secrets
            
        Returns:
            List of secret names
        """
        if include_expired:
            return list(self._secrets.keys())
        
        return [
            name for name in self._secrets.keys()
            if not self._is_expired(name) and not name.endswith('_OLD')
        ]
    
    def get_secrets_due_for_rotation(self, days_ahead: int = 7) -> List[str]:
        """
        Get secrets that need rotation soon.
        
        Args:
            days_ahead: Look ahead this many days
            
        Returns:
            List of secret names due for rotation
        """
        threshold = datetime.utcnow() + timedelta(days=days_ahead)
        
        due_secrets = []
        for name, rotation_date in self._rotation_schedule.items():
            if rotation_date <= threshold:
                due_secrets.append(name)
        
        return due_secrets
    
    def cleanup_old_secrets(self):
        """Remove expired old secret versions."""
        now = datetime.utcnow()
        to_remove = []
        
        for name, secret_data in self._secrets.items():
            if name.endswith('_OLD'):
                expires_at = secret_data.get('expires_at')
                if expires_at and now > expires_at:
                    to_remove.append(name)
        
        for name in to_remove:
            del self._secrets[name]
            logger.info("old_secret_removed", name=name)
        
        return len(to_remove)
    
    def _is_expired(self, name: str) -> bool:
        """Check if a secret has expired."""
        if name not in self._secrets:
            return False
        
        expires_at = self._secrets[name].get('expires_at')
        if not expires_at:
            return False
        
        return datetime.utcnow() > expires_at
    
    def _log_access(self, name: str, success: bool):
        """Log secret access for audit trail."""
        self._access_log.append({
            'secret_name': name,
            'timestamp': datetime.utcnow().isoformat(),
            'success': success,
        })
        
        # Keep only last 1000 entries
        if len(self._access_log) > 1000:
            self._access_log = self._access_log[-1000:]
    
    def get_access_log(self, name: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get access log entries.
        
        Args:
            name: Filter by secret name (optional)
            limit: Maximum entries to return
            
        Returns:
            List of access log entries
        """
        if name:
            filtered = [entry for entry in self._access_log if entry['secret_name'] == name]
        else:
            filtered = self._access_log
        
        return filtered[-limit:]
    
    def export_secrets_template(self, filepath: str, include_values: bool = False):
        """
        Export secrets template to file.
        
        Args:
            filepath: Output file path
            include_values: Whether to include actual values (WARNING: sensitive!)
            
        Examples:
            >>> manager.export_secrets_template('.env.template', include_values=False)
        """
        with open(filepath, 'w') as f:
            f.write("# StockIQ Secrets Configuration\n")
            f.write(f"# Generated: {datetime.utcnow().isoformat()}\n\n")
            
            for name in sorted(self._secrets.keys()):
                if name.endswith('_OLD'):
                    continue
                
                if include_values:
                    value = self._secrets[name]['value']
                else:
                    value = "your_secret_here"
                
                f.write(f"{name}={value}\n")
        
        logger.info("secrets_template_exported", filepath=filepath)


# ============================================================================
# API-Specific Secret Managers
# ============================================================================

class APIKeyManager:
    """
    Manages API keys for external services.
    
    Provides simplified interface for common API key operations.
    """
    
    def __init__(self, secrets_manager: Optional[SecretsManager] = None):
        """
        Initialize API key manager.
        
        Args:
            secrets_manager: SecretsManager instance (creates new if None)
        """
        self.secrets = secrets_manager or SecretsManager()
        
        # Map service names to environment variable names
        self._service_mapping = {
            'newsapi': 'NEWSAPI_API_KEY',
            'finnhub': 'FINNHUB_API_KEY',
            'alpha_vantage': 'ALPHA_VANTAGE_API_KEY',
            'polygon': 'POLYGON_API_KEY',
            'alpaca': 'ALPACA_API_KEY',
        }
    
    def get_api_key(self, service: str) -> str:
        """
        Get API key for a service.
        
        Args:
            service: Service name (newsapi, finnhub, alpha_vantage, etc.)
            
        Returns:
            API key
            
        Raises:
            SecretNotFoundError: If API key not found
            
        Examples:
            >>> manager = APIKeyManager()
            >>> key = manager.get_api_key('newsapi')
        """
        env_var = self._service_mapping.get(service)
        if not env_var:
            raise ValueError(f"Unknown service: {service}")
        
        return self.secrets.get_secret(env_var)
    
    def rotate_api_key(self, service: str, new_key: str, grace_period_days: int = 7):
        """
        Rotate API key for a service.
        
        Args:
            service: Service name
            new_key: New API key
            grace_period_days: Grace period for old key
            
        Examples:
            >>> manager.rotate_api_key('newsapi', 'new_key_value', grace_period_days=7)
        """
        env_var = self._service_mapping.get(service)
        if not env_var:
            raise ValueError(f"Unknown service: {service}")
        
        self.secrets.rotate_secret(env_var, new_key, grace_period_days)
        
        logger.info(
            "api_key_rotated",
            service=service,
            grace_period_days=grace_period_days
        )
    
    def validate_api_key(self, service: str, key: str) -> bool:
        """
        Validate API key for a service.
        
        Args:
            service: Service name
            key: API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        env_var = self._service_mapping.get(service)
        if not env_var:
            return False
        
        return self.secrets.validate_secret(env_var, key)
    
    def get_masked_api_key(self, service: str) -> str:
        """
        Get masked API key for display/logging.
        
        Args:
            service: Service name
            
        Returns:
            Masked API key
        """
        try:
            key = self.get_api_key(service)
            return self.secrets.mask_secret(key)
        except SecretNotFoundError:
            return "***"
    
    def list_services(self) -> List[str]:
        """Get list of supported services."""
        return list(self._service_mapping.keys())
    
    def get_service_status(self, service: str) -> Dict[str, Any]:
        """
        Get status information for a service's API key.
        
        Args:
            service: Service name
            
        Returns:
            Dictionary with status information
        """
        env_var = self._service_mapping.get(service)
        if not env_var:
            raise ValueError(f"Unknown service: {service}")
        
        try:
            metadata = self.secrets.get_secret_metadata(env_var)
            return {
                'service': service,
                'key_masked': self.get_masked_api_key(service),
                **metadata
            }
        except SecretNotFoundError:
            return {
                'service': service,
                'status': 'not_configured',
                'error': 'API key not found'
            }


# ============================================================================
# Global Instances
# ============================================================================

# Global secrets manager (lazy initialization)
_secrets_manager: Optional[SecretsManager] = None
_api_key_manager: Optional[APIKeyManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create the global secrets manager."""
    global _secrets_manager
    
    if _secrets_manager is None:
        # Try to load from .env file in project root
        env_file = os.getenv('ENV_FILE', '.env')
        if os.path.exists(env_file):
            _secrets_manager = SecretsManager(env_file)
        else:
            _secrets_manager = SecretsManager()
    
    return _secrets_manager


def get_api_key_manager() -> APIKeyManager:
    """Get or create the global API key manager."""
    global _api_key_manager
    
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager(get_secrets_manager())
    
    return _api_key_manager


# ============================================================================
# Convenience Functions
# ============================================================================

def get_api_key(service: str) -> str:
    """
    Get API key for a service (convenience function).
    
    Args:
        service: Service name
        
    Returns:
        API key
        
    Examples:
        >>> from stockiq.infrastructure.secrets import get_api_key
        >>> key = get_api_key('newsapi')
    """
    manager = get_api_key_manager()
    return manager.get_api_key(service)


def rotate_api_key(service: str, new_key: str, grace_period_days: int = 7):
    """
    Rotate API key for a service (convenience function).
    
    Args:
        service: Service name
        new_key: New API key
        grace_period_days: Grace period for old key
        
    Examples:
        >>> from stockiq.infrastructure.secrets import rotate_api_key
        >>> rotate_api_key('newsapi', 'new_key_value', grace_period_days=7)
    """
    manager = get_api_key_manager()
    manager.rotate_api_key(service, new_key, grace_period_days)
