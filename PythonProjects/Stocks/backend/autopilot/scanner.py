"""
CandidateScanner — finds tradeable candidates for AutoPilot.

Given a market_type ("penny" | "regular") and a set of filters, it walks the
provider's universe, pulls quotes + intraday bars, computes a momentum score
from price action / volume surge / RSI / MACD, and returns a ranked shortlist.

The scanner is provider-agnostic: it only uses the MarketDataProvider
interface, so swapping data vendors requires no changes here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from autotrade.strategies import rsi, macd
from autopilot.providers import MarketDataProvider, Quote

logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    """A ranked trade candidate produced by the scanner."""
    ticker: str
    price: float
    change_pct: float
    volume_ratio: float
    momentum_score: float          # 0–100 composite
    rsi: Optional[float] = None
    macd_hist: Optional[float] = None
    indicators: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "price": round(self.price, 4),
            "change_pct": round(self.change_pct, 2),
            "volume_ratio": round(self.volume_ratio, 2),
            "momentum_score": round(self.momentum_score, 1),
            "rsi": round(self.rsi, 1) if self.rsi is not None else None,
            "macd_hist": round(self.macd_hist, 4) if self.macd_hist is not None else None,
        }


@dataclass
class ScanFilters:
    """Universe filter parameters, sourced from an AutoPilotConfigDB row."""
    market_type: str
    min_price: float
    max_price: float
    min_change_pct: float
    min_volume_ratio: float
    max_candidates: int


class CandidateScanner:
    """Scans the provider universe for momentum candidates."""

    def __init__(self, provider: MarketDataProvider) -> None:
        self.provider = provider

    def scan(self, filters: ScanFilters) -> List[Candidate]:
        """
        Return up to ``max_candidates`` ranked candidates for the market type.

        Pipeline per ticker:
          1. Quote → apply price band + min change + volume-surge filters
          2. Intraday bars → RSI / MACD
          3. Composite momentum score
        Survivors are sorted by momentum_score descending.
        """
        universe = self.provider.get_universe(filters.market_type)
        if not universe:
            logger.warning("Empty universe for market_type=%s", filters.market_type)
            return []

        logger.info(
            "AutoPilot scan: %s universe=%d price=[%.2f,%.2f] minChg=%.1f%% minVol=%.1fx",
            filters.market_type, len(universe), filters.min_price,
            filters.max_price, filters.min_change_pct, filters.min_volume_ratio,
        )

        candidates: List[Candidate] = []
        for ticker in universe:
            try:
                cand = self._evaluate(ticker, filters)
                if cand is not None:
                    candidates.append(cand)
            except Exception as exc:
                logger.debug("Candidate eval failed for %s: %s", ticker, exc)

        candidates.sort(key=lambda c: c.momentum_score, reverse=True)
        top = candidates[: filters.max_candidates]
        logger.info("AutoPilot scan found %d candidates (returning top %d)",
                    len(candidates), len(top))
        return top

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _evaluate(self, ticker: str, f: ScanFilters) -> Optional[Candidate]:
        quote = self.provider.get_quote(ticker)
        if quote is None:
            return None

        # --- hard filters ---
        if not (f.min_price <= quote.price <= f.max_price):
            return None
        if quote.change_pct < f.min_change_pct:
            return None
        if quote.volume_ratio < f.min_volume_ratio:
            return None

        # --- indicators from intraday bars ---
        bars = self.provider.get_bars(ticker, period="5d", interval="5m")
        r = macd_hist = None
        if len(bars) >= 35:
            closes = [b.close for b in bars]
            r = rsi(closes, 14)
            _, _, macd_hist = macd(closes)

        score = self._momentum_score(quote, r, macd_hist)
        return Candidate(
            ticker=quote.ticker,
            price=quote.price,
            change_pct=quote.change_pct,
            volume_ratio=quote.volume_ratio,
            momentum_score=score,
            rsi=r,
            macd_hist=macd_hist,
            indicators={
                "change_pct": quote.change_pct,
                "volume_ratio": quote.volume_ratio,
                "rsi": r,
                "macd_hist": macd_hist,
            },
        )

    @staticmethod
    def _momentum_score(quote: Quote, r: Optional[float], macd_hist: Optional[float]) -> float:
        """
        Composite 0–100 momentum score.

        Weights:
          - intraday % change      40%  (capped at +10% → full marks)
          - volume surge ratio     30%  (capped at 5x → full marks)
          - RSI in the 55–75 zone  20%  (sweet spot for continuation)
          - MACD histogram > 0     10%  (bullish momentum confirmation)
        """
        # Price change component (0–40)
        chg = max(0.0, min(quote.change_pct, 10.0)) / 10.0 * 40.0

        # Volume component (0–30)
        vol = max(0.0, min(quote.volume_ratio, 5.0)) / 5.0 * 30.0

        # RSI component (0–20): peak at ~65, taper outside 55–75
        rsi_comp = 0.0
        if r is not None:
            if 55 <= r <= 75:
                rsi_comp = 20.0 - abs(65 - r)  # max 20 at 65
                rsi_comp = max(0.0, rsi_comp)
            elif 45 <= r < 55:
                rsi_comp = 10.0
            elif r > 75:
                rsi_comp = 5.0  # overbought — reduce

        # MACD component (0–10)
        macd_comp = 10.0 if (macd_hist is not None and macd_hist > 0) else 0.0

        return round(chg + vol + rsi_comp + macd_comp, 1)
