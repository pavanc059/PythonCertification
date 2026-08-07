"""
Configuration management for the application.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql://user:password@localhost:5432/stockiq",
        env="DATABASE_URL"
    )
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    redis_socket_keepalive: bool = Field(default=True, env="REDIS_SOCKET_KEEPALIVE")
    redis_socket_connect_timeout: int = Field(default=5, env="REDIS_SOCKET_CONNECT_TIMEOUT")
    redis_health_check_interval: int = Field(default=30, env="REDIS_HEALTH_CHECK_INTERVAL")
    
    # Redis Sentinel Configuration (for production HA)
    redis_sentinel_hosts: Optional[str] = Field(default=None, env="REDIS_SENTINEL_HOSTS")
    redis_sentinel_master: str = Field(default="stockiq-master", env="REDIS_SENTINEL_MASTER")
    redis_sentinel_socket_timeout: float = Field(default=0.5, env="REDIS_SENTINEL_SOCKET_TIMEOUT")
    
    # Celery Configuration
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        env="CELERY_RESULT_BACKEND"
    )
    celery_worker_concurrency: int = Field(
        default=4,
        env="CELERY_WORKER_CONCURRENCY"
    )
    celery_worker_max_tasks_per_child: int = Field(
        default=1000,
        env="CELERY_WORKER_MAX_TASKS_PER_CHILD"
    )
    celery_task_time_limit: int = Field(
        default=3600,
        env="CELERY_TASK_TIME_LIMIT"
    )
    celery_task_soft_time_limit: int = Field(
        default=3000,
        env="CELERY_TASK_SOFT_TIME_LIMIT"
    )
    
    # API Keys
    newsapi_key: Optional[str] = Field(default=None, env="NEWSAPI_KEY")
    finnhub_api_key: Optional[str] = Field(default=None, env="FINNHUB_API_KEY")
    alphavantage_api_key: Optional[str] = Field(default=None, env="ALPHAVANTAGE_API_KEY")
    polygon_api_key: Optional[str] = Field(default=None, env="POLYGON_API_KEY")
    alpaca_api_key: Optional[str] = Field(default=None, env="ALPACA_API_KEY")
    alpaca_secret_key: Optional[str] = Field(default=None, env="ALPACA_SECRET_KEY")
    
    # SEC EDGAR Configuration
    sec_user_agent: str = Field(
        default="StockIQ/1.0 (institutional@example.com)",
        env="SEC_USER_AGENT"
    )
    
    # Application Settings
    app_env: str = Field(default="development", env="APP_ENV")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Email Configuration
    smtp_host: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, env="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    smtp_from: str = Field(
        default="noreply@stockanalyzer.com",
        env="SMTP_FROM"
    )
    
    # Security
    secret_key: str = Field(
        default="change_this_in_production",
        env="SECRET_KEY"
    )
    jwt_secret_key: str = Field(
        default="change_this_in_production",
        env="JWT_SECRET_KEY"
    )
    
    # Feature Flags
    enable_real_time_streaming: bool = Field(
        default=False,
        env="ENABLE_REAL_TIME_STREAMING"
    )
    enable_deep_learning: bool = Field(
        default=False,
        env="ENABLE_DEEP_LEARNING"
    )
    enable_alternative_data: bool = Field(
        default=False,
        env="ENABLE_ALTERNATIVE_DATA"
    )
    
    # Rate Limiting (requests per time window)
    yfinance_rate_limit: int = Field(default=2000, env="YFINANCE_RATE_LIMIT")
    newsapi_rate_limit: int = Field(default=100, env="NEWSAPI_RATE_LIMIT")
    finnhub_rate_limit: int = Field(default=60, env="FINNHUB_RATE_LIMIT")
    alphavantage_rate_limit: int = Field(default=5, env="ALPHAVANTAGE_RATE_LIMIT")
    
    # Cache TTL (seconds)
    price_cache_ttl: int = Field(default=300, env="PRICE_CACHE_TTL")  # 5 minutes
    news_cache_ttl: int = Field(default=3600, env="NEWS_CACHE_TTL")  # 1 hour
    prediction_cache_ttl: int = Field(
        default=86400,
        env="PREDICTION_CACHE_TTL"
    )  # 24 hours
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
