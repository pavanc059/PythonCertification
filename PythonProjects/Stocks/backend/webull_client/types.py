"""
WebullQuoteData — normalized quote type for the Webull integration.

This is the canonical internal representation of a market quote,
regardless of which provider (webull, yfinance, stub) served the data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class WebullQuoteData:
    """Normalized quote data returned by WebullClient and its fallbacks.

    Fields match the shape described in the design doc (Model 3).
    Optional fields are set to None when the raw provider response
    does not include them.
    """

    ticker: str
    company_name: str
    price: float
    change: float
    change_pct: float
    volume: Optional[int]
    day_high: Optional[float]
    day_low: Optional[float]
    week_52_high: Optional[float]
    week_52_low: Optional[float]
    market_cap: Optional[float]
    source: str = field(default="webull")  # "webull" | "yfinance" | "stub"

    def to_dict(self) -> dict:
        """Serialize all fields to a plain dict.

        The dict can be used to reconstruct an equivalent WebullQuoteData
        via ``WebullQuoteData(**data.to_dict())``, satisfying the round-trip
        property (Requirements 14.4 / Property 9).
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WebullQuoteData":
        """Construct a WebullQuoteData from a plain dict (e.g. from to_dict()).

        Provides a convenient inverse of to_dict() for the round-trip test.
        """
        return cls(
            ticker=data["ticker"],
            company_name=data["company_name"],
            price=data["price"],
            change=data["change"],
            change_pct=data["change_pct"],
            volume=data["volume"],
            day_high=data["day_high"],
            day_low=data["day_low"],
            week_52_high=data["week_52_high"],
            week_52_low=data["week_52_low"],
            market_cap=data["market_cap"],
            source=data.get("source", "webull"),
        )
