"""
Momentum scoring for penny stocks.

Calculates composite momentum scores based on four weighted components:
  - Price component  (40%): magnitude of percentage gain
  - Volume component (30%): volume surge ratio
  - Trend component  (20%): consecutive up-days consistency
  - Catalyst component (10%): presence of a news/earnings/regulatory catalyst

Properties implemented:
  - Property 45: overall_score is always in [0, 100]
  - Property 46: component weights sum to exactly 100% (40 + 30 + 20 + 10)
  - Property 54: rank_by_momentum sorts stocks in descending order by score

Requirements: 11.4, 11.5, 11.9
"""

import logging
from typing import List, Optional

from .scanner import PennyStock

# PennyStock is defined in scanner.py (same package).
# MomentumScore is defined below in this module.

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependencies — graceful degradation
# ---------------------------------------------------------------------------

try:
    from ...infrastructure.cache import get_cache, CacheKeyPatterns, CacheTTL
    CACHE_AVAILABLE = True
except Exception:
    CACHE_AVAILABLE = False
    logger.warning("Redis cache not available — momentum caching disabled")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    from ...infrastructure.database import get_db_context
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

from dataclasses import dataclass


@dataclass
class MomentumScore:
    """
    Composite momentum score for a penny stock.

    overall_score is always in [0, 100] (Property 45).
    The four component weights sum to 100% (Property 46):
      price_component  × 0.40
      volume_component × 0.30
      trend_component  × 0.20
      catalyst_component × 0.10
    """
    overall_score: float      # 0-100 (Property 45)
    price_component: float    # 0-100 contribution from price change
    volume_component: float   # 0-100 contribution from volume surge
    trend_component: float    # 0-100 contribution from trend consistency
    catalyst_component: float # 0-100 contribution from catalyst presence


# ---------------------------------------------------------------------------
# Component weight constants — must sum to 1.0 (Property 46)
# ---------------------------------------------------------------------------

PRICE_WEIGHT: float = 0.40
VOLUME_WEIGHT: float = 0.30
TREND_WEIGHT: float = 0.20
CATALYST_WEIGHT: float = 0.10

assert abs(PRICE_WEIGHT + VOLUME_WEIGHT + TREND_WEIGHT + CATALYST_WEIGHT - 1.0) < 1e-9, (
    "Component weights must sum to exactly 1.0 (Property 46)"
)


# ---------------------------------------------------------------------------
# MomentumCalculator
# ---------------------------------------------------------------------------


class MomentumCalculator:
    """
    Calculates momentum scores for penny stocks.

    All component scores are normalised to [0, 100] before weighting so the
    resulting overall_score is also guaranteed to be in [0, 100] (Property 45).

    Redis caching is used with a 2-minute TTL when available.
    """

    #: Cache TTL in seconds (2 minutes — matches penny stock update frequency)
    CACHE_TTL_SECONDS: int = 120  # == CacheTTL.PENNY_MOMENTUM

    def __init__(self):
        self._cache = None
        if CACHE_AVAILABLE:
            try:
                self._cache = get_cache()
            except Exception as exc:
                logger.warning("Could not connect to Redis: %s", exc)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def calculate_momentum_score(self, stock: PennyStock) -> MomentumScore:
        """
        Calculate a composite momentum score for a penny stock.

        Implements Properties 45 and 46:
          - Property 45: overall_score ∈ [0, 100]
          - Property 46: component weights sum to 100%
                         (price 40% + volume 30% + trend 20% + catalyst 10%)

        Args:
            stock: PennyStock to score.

        Returns:
            MomentumScore with overall_score and individual components.
        """
        # Try cache first
        cache_key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.PENNY_MOMENTUM, ticker=stock.ticker
        ) if CACHE_AVAILABLE else None
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # --- Price component (40%) ---
        # Normalise price_change_pct to [0, 100].
        # A gain of ≥ 100% maps to a full score of 100; proportional below that.
        price_component = self._calculate_price_component(stock.price_change_pct)

        # --- Volume component (30%) ---
        # Based on the volume surge ratio (current / average).
        # A ratio of ≥ 10x maps to 100; proportional below that.
        volume_component = self._calculate_volume_component(stock.volume_ratio)

        # --- Trend component (20%) ---
        # Based on consecutive up days stored on the stock, or estimated
        # from available data.  A streak of ≥ 5 days maps to 100.
        trend_component = self._calculate_trend_component(stock)

        # --- Catalyst component (10%) ---
        # Binary signal: 100 if a catalyst is present, else 0.
        catalyst_component = self._calculate_catalyst_component(stock)

        # --- Composite score (Property 46 weight verification) ---
        # Weights: 0.40 + 0.30 + 0.20 + 0.10 = 1.00
        overall = (
            price_component * PRICE_WEIGHT
            + volume_component * VOLUME_WEIGHT
            + trend_component * TREND_WEIGHT
            + catalyst_component * CATALYST_WEIGHT
        )

        # Clamp to [0, 100] to satisfy Property 45 despite floating-point arithmetic
        overall = max(0.0, min(100.0, overall))

        score = MomentumScore(
            overall_score=overall,
            price_component=price_component,
            volume_component=volume_component,
            trend_component=trend_component,
            catalyst_component=catalyst_component,
        )

        self._set_in_cache(cache_key, score)
        logger.debug(
            "momentum_score ticker=%s overall=%.2f (price=%.2f vol=%.2f "
            "trend=%.2f catalyst=%.2f)",
            stock.ticker, overall,
            price_component, volume_component, trend_component, catalyst_component,
        )
        return score

    def rank_by_momentum(self, stocks: List[PennyStock]) -> List[PennyStock]:
        """
        Rank penny stocks by their momentum score in descending order.

        Implements Property 54: for any list of penny stocks, the result is
        sorted so that stocks[i].momentum_score >= stocks[i+1].momentum_score.

        Scores are calculated via calculate_momentum_score() if not already
        present on the stock object.

        Args:
            stocks: List of PennyStock objects.

        Returns:
            New list sorted by momentum score descending (highest first).
        """
        scored: List[PennyStock] = []
        for stock in stocks:
            if stock.momentum_score is None:
                ms = self.calculate_momentum_score(stock)
                # Return a copy with momentum_score populated (dataclass is mutable)
                stock.momentum_score = ms.overall_score
            scored.append(stock)

        # Sort descending by momentum_score (Property 54)
        ranked = sorted(scored, key=lambda s: s.momentum_score, reverse=True)
        logger.info("rank_by_momentum: ranked %d stocks", len(ranked))
        return ranked

    def identify_catalyst(self, ticker: str) -> Optional[str]:
        """
        Identify a catalyst event for a ticker (news, earnings, regulatory).

        Implementation is deliberately defensive: if the news data
        infrastructure is not yet available the method returns None gracefully.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            A short catalyst description string, or None if no catalyst found
            or the news infrastructure is unavailable.
        """
        # --- 1. Check the database for recent news articles ---
        if DB_AVAILABLE:
            catalyst = self._query_catalyst_from_db(ticker)
            if catalyst:
                return catalyst

        # --- 2. Cache check for previously identified catalysts ---
        catalyst_cache_key = f"penny:catalyst:{ticker}"
        cached = self._get_from_cache(catalyst_cache_key)
        if cached is not None:
            return cached

        # --- 3. Graceful degradation: no catalyst data available ---
        logger.debug("identify_catalyst: no catalyst found for %s", ticker)
        return None

    # ------------------------------------------------------------------
    # Component calculation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_price_component(price_change_pct: float) -> float:
        """
        Normalise price_change_pct to a [0, 100] score.

        Mapping:
          ≤ 0%    → 0
          0%–100% → linear 0–100
          ≥ 100%  → 100

        Only positive gains contribute to the price momentum score.
        """
        if price_change_pct <= 0.0:
            return 0.0
        # Clamp at 100% gain → score 100
        return min(price_change_pct, 100.0)

    @staticmethod
    def _calculate_volume_component(volume_ratio: float) -> float:
        """
        Normalise volume_ratio to a [0, 100] score.

        Mapping:
          ≤ 1x   → 0    (below-average volume contributes nothing)
          1x–10x → linear 0–100
          ≥ 10x  → 100

        A volume surge of 10× or more earns the maximum component score.
        """
        if volume_ratio <= 1.0:
            return 0.0
        # Scale: 1× → 0, 10× → 100
        normalised = (volume_ratio - 1.0) / (10.0 - 1.0) * 100.0
        return min(normalised, 100.0)

    @staticmethod
    def _calculate_trend_component(stock: PennyStock) -> float:
        """
        Estimate trend strength from available stock data.

        If the stock has no explicit consecutive-up-days attribute we use the
        price_change_pct and volume_ratio as a proxy:
          - Any positive gain indicates at least 1 "up" day.
          - Higher gain + higher volume → stronger trend signal.

        A full score (100) requires a ≥ 5-day consecutive up streak.
        Since the PennyStock dataclass doesn't carry consecutive_up_days
        directly, we derive an *estimated* streak from price momentum:
          estimated_streak = price_change_pct / 10  (capped at 5)

        Callers that attach a `consecutive_up_days` attribute to the stock
        will get an exact calculation.
        """
        # Use explicit attribute if present (duck-typing, forward-compatible)
        consecutive_days = getattr(stock, "consecutive_up_days", None)
        if consecutive_days is not None:
            # 5 or more consecutive up days → full score
            normalised = (float(consecutive_days) / 5.0) * 100.0
            return min(max(normalised, 0.0), 100.0)

        # Proxy estimation: every 10% gain ≈ 1 up day, cap at 5 days
        if stock.price_change_pct <= 0.0:
            return 0.0
        estimated_streak = stock.price_change_pct / 10.0
        normalised = (min(estimated_streak, 5.0) / 5.0) * 100.0
        return min(max(normalised, 0.0), 100.0)

    @staticmethod
    def _calculate_catalyst_component(stock: PennyStock) -> float:
        """
        Return 100.0 if a catalyst is present on the stock, else 0.0.

        A catalyst is considered present if:
          - stock.catalyst is a non-empty string, OR
          - any known catalyst attribute is set.
        """
        if stock.catalyst and stock.catalyst.strip():
            return 100.0
        return 0.0

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _query_catalyst_from_db(self, ticker: str) -> Optional[str]:
        """
        Query the database for recent news / earnings / regulatory events.
        Returns a short description string, or None.
        """
        try:
            from ...infrastructure.models import NewsArticle  # type: ignore
            from datetime import datetime, timedelta

            cutoff = datetime.utcnow() - timedelta(hours=24)
            with get_db_context() as db:
                row = (
                    db.query(NewsArticle)
                    .filter(
                        NewsArticle.published_at >= cutoff,
                        NewsArticle.tickers.contains(ticker),
                    )
                    .order_by(NewsArticle.published_at.desc())
                    .first()
                )
                if row:
                    return f"news:{row.title[:80]}"
            return None
        except Exception as exc:
            logger.debug("DB catalyst query failed for %s: %s", ticker, exc)
            return None

    def _get_from_cache(self, key: Optional[str]):
        """Safely retrieve a value from the Redis cache."""
        if self._cache is None or key is None:
            return None
        try:
            return self._cache.get(key)
        except Exception as exc:
            logger.debug("Cache get failed for key '%s': %s", key, exc)
            return None

    def _set_in_cache(self, key: Optional[str], value) -> None:
        """Safely store a value in the Redis cache with the 2-minute TTL."""
        if self._cache is None or key is None:
            return
        try:
            self._cache.set(key, value, ttl=self.CACHE_TTL_SECONDS)
        except Exception as exc:
            logger.debug("Cache set failed for key '%s': %s", key, exc)
