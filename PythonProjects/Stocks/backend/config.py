"""
Centralised application settings.

Both ``main.py`` and ``dependencies.py`` (and any auth module that needs the
JWT secret) import from here to avoid circular-import problems that would
arise if ``dependencies.py`` imported from ``main.py``.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    secret_key: str = "dev-secret-key"
    access_token_expire_minutes: int = 480   # 8 hours
    refresh_token_expire_days: int = 30
    database_url: str = "postgresql://stockiq:stockiq@localhost:5432/stockiq"
    redis_url: str = "redis://localhost:6379/0"
    frontend_origin: str = "http://localhost:5173"

    # ---------------------------------------------------------------------------
    # Webull OpenAPI configuration (Requirement 11.1)
    # webull_trading_pin is stored here but MUST NOT be forwarded to any client
    # call or returned in any API response (Requirement 2.2, 11.3).
    # ---------------------------------------------------------------------------
    webull_app_key: str = "03d6ca7a1cb6d56724b3d60590a8c6ba"
    webull_app_secret: str = "9669f68b866fdfd60945e8668b2d9743"
    webull_region_id: str = "us"
    webull_endpoint: str = "api.webull.com"
    webull_sandbox: bool = False
    webull_trading_pin: Optional[str] = None   # stored only; never passed to WebullClient

    # Market data provider: "webull" | "yfinance" | "stub" (Requirement 11.2)
    market_data_source: str = "webull"

    # Third-party news / data API keys
    finnhub_api_key: str = ""
    alphavantage_api_key: str = ""
    newsapi_key: str = ""

    # AI / RAG pipeline
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    tavily_api_key: str = ""
    groq_api_key: str = ""   # free alternative — Llama 3.3 70B via Groq

    # ---------------------------------------------------------------------------
    # AutoPilot (automated day-trader)
    # ---------------------------------------------------------------------------
    # Pluggable market-data provider for AutoPilot scanning / quotes.
    # Supported: "yfinance" (default). Future: "webull", "polygon", "alpaca".
    autopilot_data_provider: str = "yfinance"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
