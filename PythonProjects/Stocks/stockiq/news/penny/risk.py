"""
Penny stock risk analysis and pump-dump detection.

Implements:
  - PennyStockRiskAnalyzer: risk metrics calculation (Properties 48, 49, 50)
  - PumpDumpDetector: suspicious pattern detection (Properties 51, 52)

Properties implemented:
  - Property 48: liquidity_risk always in [0, 1]
  - Property 49: spread_percentage always >= 0
  - Property 50: overall_risk always one of 'low', 'medium', 'high', 'extreme'
  - Property 51: suspicion score always in [0, 1]
  - Property 52: high-priority alert when intraday gain > 100%

Requirements: 11.10, 11.13, 11.14
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from .scanner import PennyStock, RiskMetrics

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependencies — graceful degradation
# ---------------------------------------------------------------------------

try:
    from ...infrastructure.database import get_db_context
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False
    logger.warning("Database not available — risk metrics DB storage disabled")

try:
    from ...infrastructure.cache import get_cache
    CACHE_AVAILABLE = True
except Exception:
    CACHE_AVAILABLE = False
    logger.warning("Redis cache not available — risk caching disabled")


# ---------------------------------------------------------------------------
# Additional data models
# ---------------------------------------------------------------------------

@dataclass
class RiskAssessment:
    """Full risk assessment for a penny stock."""
    ticker: str
    liquidity_risk: float    # 0-1
    volatility_risk: float   # 0-1
    spread_percentage: float # >= 0
    overall_risk: str        # 'low', 'medium', 'high', or 'extreme'
    composite_score: float   # 0-1 composite used to derive overall_risk

    #: Valid risk classification levels (Property 50)
    VALID_RISK_LEVELS = frozenset({"low", "medium", "high", "extreme"})


@dataclass
class SuspicionScore:
    """Pump-and-dump suspicion score for a penny stock."""
    score: float             # 0-1, higher = more suspicious (Property 51)
    indicators: List[str]    # Human-readable list of triggered indicators
    recommendation: str      # 'safe', 'caution', or 'avoid'

    #: Valid recommendations
    VALID_RECOMMENDATIONS = frozenset({"safe", "caution", "avoid"})


@dataclass
class InsiderActivity:
    """Insider trading activity summary for a ticker."""
    ticker: str
    recent_buys: int
    recent_sells: int
    net_activity: str  # 'buying', 'selling', or 'neutral'
    suspicious: bool


# ---------------------------------------------------------------------------
# Risk thresholds
# ---------------------------------------------------------------------------

# Liquidity risk thresholds (avg_volume)
_LIQUIDITY_LOW_VOLUME = 50_000        # below this → high liquidity risk
_LIQUIDITY_MED_VOLUME = 200_000       # below this → medium liquidity risk

# Market cap thresholds for liquidity risk contribution
_MARKET_CAP_MICRO = 10_000_000        # < $10M → very high liquidity risk
_MARKET_CAP_SMALL = 50_000_000        # < $50M → moderate liquidity risk

# Volatility proxy thresholds (|price_change_pct|)
_VOLATILITY_HIGH_CHANGE = 50.0        # >= 50% change → high volatility
_VOLATILITY_MED_CHANGE = 20.0         # >= 20% change → medium volatility

# Spread assumption — penny stocks typically have 1–5% spreads
# Used when no real bid/ask data is available.
_DEFAULT_SPREAD_PCT_PENNY = 2.0       # 2% assumed spread for penny stocks

# Overall risk classification thresholds (composite 0-1 score)
_EXTREME_RISK_THRESHOLD = 0.75
_HIGH_RISK_THRESHOLD = 0.50
_MEDIUM_RISK_THRESHOLD = 0.25


# ---------------------------------------------------------------------------
# PennyStockRiskAnalyzer
# ---------------------------------------------------------------------------

class PennyStockRiskAnalyzer:
    """
    Calculates risk metrics specific to penny stocks.

    All returned values satisfy:
      - Property 48: liquidity_risk ∈ [0, 1]
      - Property 49: spread_percentage ≥ 0
      - Property 50: overall_risk ∈ {'low', 'medium', 'high', 'extreme'}

    External dependencies (DB, cache) are used when available; the analyzer
    degrades gracefully when they are not.
    """

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

    def calculate_liquidity_risk(self, stock: PennyStock) -> float:
        """
        Calculate liquidity risk for a penny stock.

        Property 48: result is always in [0, 1].

        Risk is calculated from two factors:
          - Average daily volume (lower volume → higher risk)
          - Market capitalisation (lower cap → higher risk)

        The two sub-scores are averaged and the result is clamped to [0, 1].

        Args:
            stock: PennyStock to evaluate.

        Returns:
            Float in [0, 1] where 1.0 means extreme illiquidity.
        """
        # --- Volume sub-score ---
        if stock.avg_volume <= 0:
            volume_score = 1.0
        elif stock.avg_volume < _LIQUIDITY_LOW_VOLUME:
            # Linear interpolation: 0 vol → 1.0, low_vol → 0.8
            volume_score = 1.0 - 0.2 * (stock.avg_volume / _LIQUIDITY_LOW_VOLUME)
        elif stock.avg_volume < _LIQUIDITY_MED_VOLUME:
            # Linear interpolation: low_vol → 0.8, med_vol → 0.4
            t = (stock.avg_volume - _LIQUIDITY_LOW_VOLUME) / (
                _LIQUIDITY_MED_VOLUME - _LIQUIDITY_LOW_VOLUME
            )
            volume_score = 0.8 - 0.4 * t
        else:
            # Above medium volume threshold — scale down from 0.4 toward 0
            volume_score = max(0.0, 0.4 - 0.4 * (
                (stock.avg_volume - _LIQUIDITY_MED_VOLUME) / (10 * _LIQUIDITY_MED_VOLUME)
            ))

        # --- Market cap sub-score ---
        if stock.market_cap <= 0:
            cap_score = 1.0
        elif stock.market_cap < _MARKET_CAP_MICRO:
            cap_score = 1.0 - 0.2 * (stock.market_cap / _MARKET_CAP_MICRO)
        elif stock.market_cap < _MARKET_CAP_SMALL:
            t = (stock.market_cap - _MARKET_CAP_MICRO) / (
                _MARKET_CAP_SMALL - _MARKET_CAP_MICRO
            )
            cap_score = 0.8 - 0.4 * t
        else:
            cap_score = max(0.0, 0.4 - 0.4 * (
                (stock.market_cap - _MARKET_CAP_SMALL) / (10 * _MARKET_CAP_SMALL)
            ))

        # Combine and clamp — Property 48
        liquidity_risk = max(0.0, min(1.0, (volume_score + cap_score) / 2.0))
        logger.debug(
            "liquidity_risk ticker=%s vol_score=%.3f cap_score=%.3f result=%.3f",
            stock.ticker, volume_score, cap_score, liquidity_risk,
        )
        return liquidity_risk

    def calculate_volatility_risk(self, stock: PennyStock) -> float:
        """
        Calculate volatility risk for a penny stock.

        Uses price_change_pct and volume_ratio as proxies for ATR/historical
        volatility, since the PennyStock dataclass does not carry full OHLC
        history.

        Returns a float in [0, 1] where 1.0 = extreme volatility.

        Args:
            stock: PennyStock to evaluate.

        Returns:
            Float in [0, 1].
        """
        # Price-change proxy: normalise |price_change_pct| to [0, 1]
        # A move of >= 100% maps to 1.0
        abs_change = abs(stock.price_change_pct)
        if abs_change <= 0.0:
            price_vol_score = 0.0
        elif abs_change >= 100.0:
            price_vol_score = 1.0
        else:
            price_vol_score = abs_change / 100.0

        # Volume-surge proxy: high volume with price move → more volatile
        # volume_ratio >= 10 → vol_score = 1.0; proportional below that
        volume_ratio = max(0.0, stock.volume_ratio)
        if volume_ratio <= 1.0:
            vol_surge_score = 0.0
        elif volume_ratio >= 10.0:
            vol_surge_score = 1.0
        else:
            vol_surge_score = (volume_ratio - 1.0) / 9.0

        # Weighted combination: price change has more predictive weight
        volatility_risk = max(0.0, min(1.0, 0.7 * price_vol_score + 0.3 * vol_surge_score))
        logger.debug(
            "volatility_risk ticker=%s price_vol=%.3f vol_surge=%.3f result=%.3f",
            stock.ticker, price_vol_score, vol_surge_score, volatility_risk,
        )
        return volatility_risk

    def calculate_spread_percentage(self, stock: PennyStock) -> float:
        """
        Calculate bid-ask spread as a percentage of the mid-price.

        Property 49: result is always >= 0.

        Formula (when bid/ask are available):
            spread_pct = ((ask - bid) / mid) * 100
            where mid = (ask + bid) / 2

        Because PennyStock does not carry bid/ask fields, the method uses a
        defensive default: penny stocks typically have 1-5% spreads; 2% is
        used as a conservative default when real data is unavailable.

        If the stock has 'bid' and 'ask' attributes (e.g., attached from a
        live data feed), those are used for an exact calculation.

        Args:
            stock: PennyStock to evaluate.

        Returns:
            Float >= 0 representing spread as a percentage of mid-price.
        """
        bid = getattr(stock, "bid", None)
        ask = getattr(stock, "ask", None)

        if bid is not None and ask is not None:
            try:
                bid_f = float(bid)
                ask_f = float(ask)
                if bid_f < 0 or ask_f < 0:
                    logger.debug(
                        "spread_pct ticker=%s: negative bid/ask, using default",
                        stock.ticker,
                    )
                    return _DEFAULT_SPREAD_PCT_PENNY
                if bid_f > ask_f:
                    # Inverted market — defensively swap
                    bid_f, ask_f = ask_f, bid_f
                mid = (ask_f + bid_f) / 2.0
                if mid <= 0:
                    return 0.0
                spread_pct = ((ask_f - bid_f) / mid) * 100.0
                # Property 49: clamp to >= 0
                return max(0.0, spread_pct)
            except (TypeError, ValueError, ZeroDivisionError) as exc:
                logger.debug(
                    "spread_pct calculation failed for %s: %s — using default",
                    stock.ticker, exc,
                )

        # Defensive default — assume 2% typical penny stock spread
        return _DEFAULT_SPREAD_PCT_PENNY

    def assess_overall_risk(self, stock: PennyStock) -> RiskAssessment:
        """
        Perform a comprehensive risk assessment for a penny stock.

        Property 50: overall_risk is always one of 'low', 'medium', 'high',
        or 'extreme'.

        The composite risk score is a weighted combination of:
          - Liquidity risk (40%)
          - Volatility risk (40%)
          - Spread risk (20%, normalised from spread_pct)

        Args:
            stock: PennyStock to assess.

        Returns:
            RiskAssessment with all risk metrics populated.
        """
        liquidity_risk = self.calculate_liquidity_risk(stock)
        volatility_risk = self.calculate_volatility_risk(stock)
        spread_pct = self.calculate_spread_percentage(stock)

        # Normalise spread_pct to [0, 1]: 0% → 0.0, >= 10% → 1.0
        spread_risk = max(0.0, min(1.0, spread_pct / 10.0))

        # Weighted composite score
        composite = max(0.0, min(1.0,
            0.40 * liquidity_risk
            + 0.40 * volatility_risk
            + 0.20 * spread_risk
        ))

        # Classify — Property 50
        if composite >= _EXTREME_RISK_THRESHOLD:
            overall_risk = "extreme"
        elif composite >= _HIGH_RISK_THRESHOLD:
            overall_risk = "high"
        elif composite >= _MEDIUM_RISK_THRESHOLD:
            overall_risk = "medium"
        else:
            overall_risk = "low"

        assessment = RiskAssessment(
            ticker=stock.ticker,
            liquidity_risk=liquidity_risk,
            volatility_risk=volatility_risk,
            spread_percentage=spread_pct,
            overall_risk=overall_risk,
            composite_score=composite,
        )

        # Persist to DB and update stock object
        self._store_risk_metrics(assessment)
        stock.risk_metrics = RiskMetrics(
            liquidity_risk=liquidity_risk,
            volatility_risk=volatility_risk,
            spread_percentage=spread_pct,
            overall_risk=overall_risk,
        )

        logger.info(
            "risk_assessment ticker=%s composite=%.3f overall=%s",
            stock.ticker, composite, overall_risk,
        )
        return assessment

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _store_risk_metrics(self, assessment: RiskAssessment) -> None:
        """
        Persist risk metrics to the penny_stock_risk_metrics table.

        Fails silently if DB is unavailable (graceful degradation).
        """
        if not DB_AVAILABLE:
            return
        try:
            with get_db_context() as db:
                db.execute(
                    """
                    INSERT INTO penny_stock_risk_metrics
                        (ticker, date, liquidity_risk, volatility_risk, spread_pct)
                    VALUES (:ticker, :date, :liq, :vol, :spread)
                    ON CONFLICT (ticker, date) DO UPDATE SET
                        liquidity_risk = EXCLUDED.liquidity_risk,
                        volatility_risk = EXCLUDED.volatility_risk,
                        spread_pct = EXCLUDED.spread_pct
                    """,
                    {
                        "ticker": assessment.ticker,
                        "date": datetime.utcnow().date().isoformat(),
                        "liq": assessment.liquidity_risk,
                        "vol": assessment.volatility_risk,
                        "spread": assessment.spread_percentage,
                    },
                )
                db.commit()
        except Exception as exc:
            logger.warning(
                "Failed to store risk metrics for %s: %s", assessment.ticker, exc
            )


# ---------------------------------------------------------------------------
# PumpDumpDetector
# ---------------------------------------------------------------------------

# Suspicion score thresholds
_SUSPICION_AVOID = 0.7     # >= 0.7 → 'avoid'
_SUSPICION_CAUTION = 0.4   # >= 0.4 → 'caution'

# Abnormal volume spike threshold (without news)
_ABNORMAL_VOLUME_RATIO = 5.0   # 5× average = abnormal

# Rapid decline threshold — detected via negative price change after a spike
_RAPID_DECLINE_THRESHOLD = -20.0  # >= 20% decline from peak

# High-priority alert threshold (Property 52)
HIGH_PRIORITY_GAIN_THRESHOLD = 100.0  # > 100% intraday gain


class PumpDumpDetector:
    """
    Detects suspicious pump-and-dump patterns in penny stocks.

    Properties implemented:
      - Property 51: SuspicionScore.score is always in [0, 1]
      - Property 52: Flag high-priority alert when intraday gain > 100%

    All external service calls (SEC, social media) fail gracefully and
    return safe defaults when not available.
    """

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

    def detect_suspicious_patterns(self, stock: PennyStock) -> SuspicionScore:
        """
        Detect pump-and-dump indicators for a penny stock.

        Property 51: SuspicionScore.score is always in [0, 1].

        Indicators checked:
          1. Abnormal volume spike without a news catalyst
          2. Rapid price increase pattern (based on price_change_pct)
          3. Social media campaign signals (attempted, fails gracefully)
          4. High-priority gain flag (Property 52: gain > 100%)

        Each indicator contributes a weight to the composite score.
        The score is clamped to [0, 1] before returning.

        Args:
            stock: PennyStock to analyse.

        Returns:
            SuspicionScore with score ∈ [0, 1], triggered indicators, and
            a recommendation string.
        """
        indicators: List[str] = []
        score_accumulator = 0.0

        # --- Indicator 1: abnormal volume spike without news catalyst ---
        if stock.volume_ratio >= _ABNORMAL_VOLUME_RATIO and not stock.catalyst:
            indicators.append(
                f"Abnormal volume spike ({stock.volume_ratio:.1f}× average) "
                "without news catalyst"
            )
            score_accumulator += 0.30

        # --- Indicator 2: extreme rapid price increase ---
        if stock.price_change_pct >= HIGH_PRIORITY_GAIN_THRESHOLD:
            # Property 52: > 100% gain → high-priority indicator
            indicators.append(
                f"Extreme intraday gain ({stock.price_change_pct:.1f}%) "
                "— high-priority alert (Property 52)"
            )
            score_accumulator += 0.35
        elif stock.price_change_pct >= 50.0:
            indicators.append(
                f"Large rapid price increase ({stock.price_change_pct:.1f}%)"
            )
            score_accumulator += 0.20

        # --- Indicator 3: high volume ratio even with catalyst present ---
        if stock.volume_ratio >= _ABNORMAL_VOLUME_RATIO and stock.catalyst:
            indicators.append(
                f"Very high volume ratio ({stock.volume_ratio:.1f}×) even with catalyst"
            )
            score_accumulator += 0.10

        # --- Indicator 4: social media campaign (external — fail gracefully) ---
        social_flag = self._check_social_media_campaigns(stock.ticker)
        if social_flag:
            indicators.append("Coordinated social media campaign detected")
            score_accumulator += 0.25

        # --- Clamp to [0, 1] — Property 51 ---
        score = max(0.0, min(1.0, score_accumulator))

        recommendation = self.generate_recommendation(score)

        result = SuspicionScore(
            score=score,
            indicators=indicators,
            recommendation=recommendation,
        )
        logger.info(
            "suspicion_score ticker=%s score=%.3f rec=%s indicators=%d",
            stock.ticker, score, recommendation, len(indicators),
        )
        return result

    def check_insider_activity(self, ticker: str) -> InsiderActivity:
        """
        Check for suspicious insider trading patterns for a ticker.

        Queries SEC Form 4 filings when DB is available.
        Falls back to a neutral InsiderActivity with 0 buys/sells when not.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            InsiderActivity with recent buy/sell counts and a suspicious flag.
        """
        if DB_AVAILABLE:
            try:
                return self._query_insider_activity(ticker)
            except Exception as exc:
                logger.warning(
                    "insider_activity DB query failed for %s: %s — using neutral default",
                    ticker, exc,
                )

        # Graceful degradation: neutral activity
        return InsiderActivity(
            ticker=ticker,
            recent_buys=0,
            recent_sells=0,
            net_activity="neutral",
            suspicious=False,
        )

    def generate_recommendation(self, suspicion_score: float) -> str:
        """
        Generate a trading recommendation based on the suspicion score.

        Score ranges:
          >= 0.70 → 'avoid'
          >= 0.40 → 'caution'
          <  0.40 → 'safe'

        Args:
            suspicion_score: Float in [0, 1].

        Returns:
            One of 'safe', 'caution', or 'avoid'.
        """
        if suspicion_score >= _SUSPICION_AVOID:
            return "avoid"
        elif suspicion_score >= _SUSPICION_CAUTION:
            return "caution"
        else:
            return "safe"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_social_media_campaigns(self, ticker: str) -> bool:
        """
        Check for coordinated social media campaigns on Twitter/Reddit.

        This is an external service call — fails gracefully and returns False
        when the service is unavailable.

        In a full implementation this would query a social media API or a
        pre-computed social_buzz table in the database.

        Returns:
            True if a suspicious coordinated campaign is detected, else False.
        """
        # --- Try DB-backed social buzz table ---
        if DB_AVAILABLE:
            try:
                with get_db_context() as db:
                    row = db.execute(
                        """
                        SELECT coordinated_flag
                        FROM social_media_buzz
                        WHERE ticker = :ticker
                          AND recorded_at >= :cutoff
                        ORDER BY recorded_at DESC
                        LIMIT 1
                        """,
                        {
                            "ticker": ticker,
                            "cutoff": (
                                datetime.utcnow() - timedelta(hours=24)
                            ).isoformat(),
                        },
                    ).fetchone()
                    if row and row[0]:
                        return True
            except Exception as exc:
                logger.debug(
                    "social_media_campaigns DB query failed for %s: %s", ticker, exc
                )

        # Graceful default — no campaign detected
        return False

    def _query_insider_activity(self, ticker: str) -> InsiderActivity:
        """
        Query SEC Form 4 filings from the database for recent insider trades.

        Returns InsiderActivity with:
          - recent_buys:  purchases in the last 90 days
          - recent_sells: sales in the last 90 days
          - net_activity: 'buying', 'selling', or 'neutral'
          - suspicious:   True if significant selling during a price spike
        """
        cutoff = (datetime.utcnow() - timedelta(days=90)).isoformat()

        with get_db_context() as db:
            rows = db.execute(
                """
                SELECT transaction_type, COUNT(*) as cnt
                FROM insider_transactions
                WHERE ticker = :ticker
                  AND transaction_date >= :cutoff
                GROUP BY transaction_type
                """,
                {"ticker": ticker, "cutoff": cutoff},
            ).fetchall()

        buys = 0
        sells = 0
        for row in rows:
            tx_type = (row[0] or "").lower()
            count = int(row[1])
            if tx_type in ("purchase", "buy", "p"):
                buys += count
            elif tx_type in ("sale", "sell", "s"):
                sells += count

        if sells > buys and sells > 3:
            net_activity = "selling"
        elif buys > sells and buys > 3:
            net_activity = "buying"
        else:
            net_activity = "neutral"

        # Flag as suspicious if insiders are selling during a price spike
        suspicious = net_activity == "selling" and sells > 5

        return InsiderActivity(
            ticker=ticker,
            recent_buys=buys,
            recent_sells=sells,
            net_activity=net_activity,
            suspicious=suspicious,
        )
