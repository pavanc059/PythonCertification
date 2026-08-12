"""
WebullClient — thin wrapper around the official ``webull-openapi-python-sdk``.

This module provides:
  - WebullUnavailableError: raised when Webull returns a non-200 response,
    the SDK raises an exception, or the response body is missing expected data.
  - WebullClient: constructs ``ApiClient`` and ``DataClient`` once at init,
    then exposes read-only data fetching methods with exponential-backoff retry.

Authentication model
--------------------
The official SDK uses App Key + App Secret (not email/password).  ``ApiClient``
is constructed once with these credentials; it automatically applies HMAC-SHA1
signing to every outbound request.  There is **no** ``login()`` call, no session
token, and no background refresh task — the SDK is entirely stateless from the
application's perspective.

Read-only contract
------------------
This constructor deliberately does NOT accept a ``trading_pin`` parameter.
``WEBULL_TRADING_PIN`` is stored in ``Settings`` for reference but is NEVER
forwarded here, satisfying Requirements 1.2 and 2.1–2.2.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from .types import WebullQuoteData

logger = logging.getLogger(__name__)


class WebullUnavailableError(Exception):
    """Raised when Webull cannot be reached or the session is invalid.

    This exception is caught by WebullMarketService, which falls back to
    yfinance when it is raised.
    """


class WebullClient:
    """Thin wrapper around the official ``webull-openapi-python-sdk``.

    Constructs ``ApiClient`` and ``DataClient`` once at init.  The SDK signs
    every request automatically; there is no session management.  Implements
    exponential-backoff retry and raises typed exceptions that
    ``WebullMarketService`` catches.

    Parameters
    ----------
    app_key:
        Official SDK App Key (from Webull Developer Portal).
    app_secret:
        Official SDK App Secret.
    region_id:
        Region identifier (default: ``"us"``).
    endpoint:
        API endpoint hostname (default: ``"api.webull.com"``).

    Notes
    -----
    CRITICAL: This constructor deliberately does NOT accept a ``trading_pin``
    parameter.  ``WEBULL_TRADING_PIN`` is stored in ``Settings`` for reference
    but is NEVER forwarded here, satisfying Requirements 1.2 and 2.1–2.2
    (read-only enforcement and PIN isolation).

    No network connection is made during ``__init__``; the SDK signs requests
    on demand via HMAC-SHA1.
    """

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        region_id: str = "us",
        endpoint: str = "api.webull.com",
    ) -> None:
        # Store config attrs (never logged in full; app_key logged only for debug)
        self._app_key = app_key
        self._region_id = region_id
        self._endpoint = endpoint

        # Lazy import to avoid a crash at startup if the SDK is not installed
        from webull.core.client import ApiClient  # type: ignore[import]
        from webull.data.data_client import DataClient  # type: ignore[import]

        api_client = ApiClient(app_key, app_secret, region_id)
        api_client.add_endpoint(region_id, endpoint)
        self._data_client = DataClient(api_client)

        logger.info(
            "WebullClient constructed for region=%s endpoint=%s",
            region_id, endpoint,
        )

    # ------------------------------------------------------------------
    # Retry helper
    # ------------------------------------------------------------------

    def _retry_sdk_call(self, fn: Any, ticker_or_op: str, *args: Any, **kwargs: Any) -> Any:
        """Call ``fn(*args, **kwargs)`` with 3-attempt exponential-backoff retry.

        Treats non-200 HTTP status codes as failures.
        Raises ``WebullUnavailableError`` after all attempts fail.

        Parameters
        ----------
        fn:
            Callable to invoke.
        ticker_or_op:
            Ticker symbol or operation name used in log/error messages.
        *args, **kwargs:
            Forwarded verbatim to *fn*.

        Returns
        -------
        Any
            The return value of the first successful call.

        Raises
        ------
        WebullUnavailableError
            After all attempts are exhausted.
        """
        max_attempts = 3
        last_exc: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                res = fn(*args, **kwargs)
                if hasattr(res, "status_code") and res.status_code != 200:
                    raise ValueError(f"HTTP {res.status_code}: {getattr(res, 'text', '')}")
                return res
            except Exception as exc:
                last_exc = exc
                if attempt < max_attempts:
                    wait = 2 ** attempt
                    logger.debug(
                        "Attempt %d/%d failed for %s (%s). Retrying in %ds.",
                        attempt, max_attempts, ticker_or_op, exc, wait,
                    )
                    time.sleep(wait)
        raise WebullUnavailableError(
            f"All {max_attempts} attempts failed for {ticker_or_op}: {last_exc}"
        )

    # ------------------------------------------------------------------
    # Internal validation helpers
    # ------------------------------------------------------------------

    def _check_not_empty(self, raw: Any, ticker: str) -> None:
        """Raise ``ValueError`` if *raw* looks like an empty/invalid response.

        A response is considered empty when:
        - *raw* is ``None``, or
        - *raw* is a dict that contains none of the price-related keys
          ``"close"``, ``"price"``, or ``"latestPrice"``.

        Parameters
        ----------
        raw:
            The raw value returned by a Webull SDK call.
        ticker:
            Ticker symbol used to build the error message.

        Raises
        ------
        ValueError
            When *raw* is empty or missing expected price data.
        """
        if raw is None:
            raise ValueError(f"Empty response for {ticker}")
        if isinstance(raw, dict):
            price_keys = {"close", "price", "latestPrice"}
            if not price_keys.intersection(raw.keys()):
                raise ValueError(f"Empty response for {ticker}")

    # ------------------------------------------------------------------
    # Quote normalization
    # ------------------------------------------------------------------

    def _normalize_webull_quote(self, raw: dict, ticker: str) -> WebullQuoteData:
        """Normalize a raw official SDK ``get_snapshot()`` response into a
        ``WebullQuoteData`` object.

        Raw field mapping (official SDK)
        ---------------------------------
        * ``close``                          → ``price``
        * ``name`` or ``companyName``        → ``company_name``
        * ``change``                         → ``change``
        * ``changeRate`` or ``changeRatio``  → ``change_pct``
        * ``volume``                         → ``volume``
        * ``high``                           → ``day_high``
        * ``low``                            → ``day_low``
        * ``week52High``                     → ``week_52_high``
        * ``week52Low``                      → ``week_52_low``
        * ``marketValue`` or
          ``totalMarketValue``               → ``market_cap``

        ``source`` is always set to ``"webull"``.

        Optional fields (``volume``, ``day_high``, ``day_low``,
        ``week_52_high``, ``week_52_low``, ``market_cap``) are set to
        ``None`` when absent from the raw dict (Requirements 14.3).

        Parameters
        ----------
        raw:
            Raw dict returned by the official SDK ``get_snapshot()`` call.
        ticker:
            Ticker symbol used for error messages and as the canonical
            ``ticker`` field on the returned object.

        Returns
        -------
        WebullQuoteData
            Fully populated (with optional fields possibly ``None``)
            normalized quote object.

        Raises
        ------
        WebullUnavailableError
            If ``raw["close"]`` is ``None`` or ``0`` (Requirements 14.5).
        """
        # --- price (required) ---
        raw_price = raw.get("close")
        if raw_price is None or raw_price == 0:
            raise WebullUnavailableError(f"Invalid price for {ticker}")
        price = float(raw_price)

        # --- company_name ---
        # Official SDK uses "name"; fall back to "companyName" for compat
        company_name: str = str(raw.get("name") or raw.get("companyName") or ticker)

        # --- change and change_pct (default to 0.0 when absent) ---
        raw_change = raw.get("change")
        change: float = float(raw_change) if raw_change is not None else 0.0

        # Official SDK uses "changeRate"; keep "changeRatio" as fallback for compat
        raw_change_ratio = raw.get("changeRate") or raw.get("changeRatio")
        change_pct: float = (
            float(raw_change_ratio) if raw_change_ratio is not None else 0.0
        )

        # --- optional fields ---
        raw_volume = raw.get("volume")
        volume: Optional[int] = int(raw_volume) if raw_volume is not None else None

        raw_high = raw.get("high")
        day_high: Optional[float] = float(raw_high) if raw_high is not None else None

        raw_low = raw.get("low")
        day_low: Optional[float] = float(raw_low) if raw_low is not None else None

        raw_52h = raw.get("week52High")
        week_52_high: Optional[float] = (
            float(raw_52h) if raw_52h is not None else None
        )

        raw_52l = raw.get("week52Low")
        week_52_low: Optional[float] = (
            float(raw_52l) if raw_52l is not None else None
        )

        # marketValue takes priority; fall back to totalMarketValue
        raw_mktcap = raw.get("marketValue") if raw.get("marketValue") is not None \
            else raw.get("totalMarketValue")
        market_cap: Optional[float] = (
            float(raw_mktcap) if raw_mktcap is not None else None
        )

        return WebullQuoteData(
            ticker=ticker,
            company_name=company_name,
            price=price,
            change=change,
            change_pct=change_pct,
            volume=volume,
            day_high=day_high,
            day_low=day_low,
            week_52_high=week_52_high,
            week_52_low=week_52_low,
            market_cap=market_cap,
            source="webull",
        )

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def fetch_quote(self, ticker: str) -> dict:
        """Fetch a real-time snapshot for *ticker* from the official Webull OpenAPI.

        Calls ``data_client.market_data.get_snapshot(ticker, "US_STOCK",
        extend_hour_required=True, overnight_required=True)``.
        Returns the raw response dict. Normalization is done by
        ``WebullMarketService``.

        Parameters
        ----------
        ticker:
            Uppercase ticker symbol (1–5 characters).

        Returns
        -------
        dict
            Raw response dict from the official SDK.

        Raises
        ------
        WebullUnavailableError
            On non-200 response or missing close price.
        """
        start = time.monotonic()
        logger.debug("fetch_quote: ticker=%s", ticker)

        res = self._retry_sdk_call(
            self._data_client.market_data.get_snapshot,
            ticker,
            ticker, "US_STOCK",
            extend_hour_required=True,
            overnight_required=True,
        )
        raw = res.json()
        self._check_not_empty(raw, ticker)

        elapsed = time.monotonic() - start
        logger.debug("fetch_quote: completed ticker=%s elapsed=%.3fs", ticker, elapsed)
        return raw

    def fetch_bars(
        self,
        ticker: str,
        interval: str,
        count: int = 200,
    ) -> list[dict]:
        """Fetch OHLCV history bars for *ticker*.

        ``interval`` must be a Timespan enum name: ``"M1"``, ``"M5"``,
        ``"M15"``, ``"M30"``, ``"H1"``, ``"D1"``.

        Calls ``data_client.market_data.get_history_bar(ticker, "US_STOCK",
        interval)``.

        Parameters
        ----------
        ticker:
            Uppercase ticker symbol.
        interval:
            Webull Timespan enum name (e.g. ``"M5"``).
        count:
            Number of bars requested (default: 200; passed for callers that
            cache the count, but the official SDK controls the actual count).

        Returns
        -------
        list[dict]
            List of OHLCV bar dicts.

        Raises
        ------
        WebullUnavailableError
            On failure or empty response.
        """
        start = time.monotonic()
        logger.debug("fetch_bars: ticker=%s interval=%s", ticker, interval)

        res = self._retry_sdk_call(
            self._data_client.market_data.get_history_bar,
            ticker,
            ticker, "US_STOCK", interval,
        )
        raw = res.json()
        if not raw:
            raise WebullUnavailableError(
                f"Empty bars response for {ticker} interval={interval}"
            )
        bars = (
            raw if isinstance(raw, list)
            else list(raw.values()) if isinstance(raw, dict)
            else []
        )

        elapsed = time.monotonic() - start
        logger.debug(
            "fetch_bars: completed ticker=%s interval=%s elapsed=%.3fs",
            ticker, interval, elapsed,
        )
        return bars

    def fetch_news(self, ticker: str, count: int = 20) -> list[dict]:
        """News is not available via the official Webull OpenAPI SDK.

        Always raises ``WebullUnavailableError`` so ``WebullMarketService``
        falls back to yfinance news or stub data immediately.

        Raises
        ------
        WebullUnavailableError
            Always.
        """
        raise WebullUnavailableError(
            "News not available via official Webull OpenAPI SDK — use yfinance or stub fallback"
        )

    def fetch_movers(self) -> dict:
        """Traditional gainers/losers are not available via the official Webull OpenAPI SDK.

        Always raises ``WebullUnavailableError`` so ``WebullMarketService``
        falls back to stub data immediately.

        Raises
        ------
        WebullUnavailableError
            Always.
        """
        raise WebullUnavailableError(
            "Movers not available via official Webull OpenAPI SDK — use stub fallback"
        )
