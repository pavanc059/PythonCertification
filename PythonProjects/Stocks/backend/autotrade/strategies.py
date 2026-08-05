"""
Trading strategies for the auto-trade engine.

Each strategy consumes a rolling window of OHLCV bars and emits a Signal
(BUY / SELL / HOLD) with a confidence score. Strategies are pure functions
of price history — they hold no state and never place orders directly.
That separation lets the same strategy drive both the backtester and the
live paper-trader.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Bar:
    """A single OHLCV candle."""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class Signal:
    """A strategy's decision at a point in time."""
    type: SignalType
    confidence: float          # 0–100
    reason: str                # human-readable explanation
    indicators: dict           # snapshot of indicator values


# ---------------------------------------------------------------------------
# Indicator helpers (pure functions over a list of closes)
# ---------------------------------------------------------------------------

def sma(values: list[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(values: list[float], period: int = 14) -> Optional[float]:
    if len(values) < period + 1:
        return None
    deltas = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(values: list[float]) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Return (macd_line, signal_line, histogram) for the latest bar."""
    if len(values) < 35:
        return None, None, None
    ema12 = ema_series(values, 12)
    ema26 = ema_series(values, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    signal_line = ema_series(macd_line[25:], 9)  # skip EMA26 warmup
    if not signal_line:
        return None, None, None
    m = macd_line[-1]
    s = signal_line[-1]
    return m, s, m - s


def bollinger(values: list[float], period: int = 20, num_std: float = 2.0):
    """Return (upper, middle, lower) Bollinger Bands for the latest bar."""
    if len(values) < period:
        return None, None, None
    window = values[-period:]
    mid = sum(window) / period
    variance = sum((v - mid) ** 2 for v in window) / period
    std = variance ** 0.5
    return mid + num_std * std, mid, mid - num_std * std


# ---------------------------------------------------------------------------
# Strategy base class
# ---------------------------------------------------------------------------

class Strategy:
    """Base strategy interface. Subclasses implement evaluate()."""

    name: str = "base"
    display_name: str = "Base Strategy"
    # Minimum bars needed before the strategy can produce a signal
    min_bars: int = 30

    def __init__(self, **params) -> None:
        self.params = params

    def evaluate(self, bars: list[Bar], has_position: bool) -> Signal:
        """
        Evaluate the strategy against the price history ending at bars[-1].

        Args:
            bars: chronological OHLCV bars (oldest first)
            has_position: whether the portfolio currently holds this ticker

        Returns:
            A Signal. Strategies should only emit SELL when has_position is True
            and only emit BUY when has_position is False.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Momentum: RSI + MACD crossover
# ---------------------------------------------------------------------------

class MomentumStrategy(Strategy):
    """
    Buys when momentum turns positive (RSI rising out of neutral + MACD bullish),
    sells when momentum fades (RSI overbought or MACD turns bearish).
    """
    name = "momentum"
    display_name = "Momentum (RSI + MACD)"
    min_bars = 35

    def __init__(self, rsi_buy: float = 55, rsi_sell: float = 70, **params):
        super().__init__(rsi_buy=rsi_buy, rsi_sell=rsi_sell, **params)
        self.rsi_buy = rsi_buy
        self.rsi_sell = rsi_sell

    def evaluate(self, bars: list[Bar], has_position: bool) -> Signal:
        closes = [b.close for b in bars]
        r = rsi(closes, 14)
        m, s, hist = macd(closes)
        ind = {"rsi": r, "macd": m, "macd_signal": s, "macd_hist": hist}

        if r is None or m is None:
            return Signal(SignalType.HOLD, 0, "Insufficient data", ind)

        macd_bullish = hist is not None and hist > 0
        macd_bearish = hist is not None and hist < 0

        if not has_position:
            if r >= self.rsi_buy and macd_bullish:
                conf = min(50 + (r - self.rsi_buy) * 2 + abs(hist) * 10, 95)
                return Signal(SignalType.BUY, conf,
                              f"RSI {r:.1f} ≥ {self.rsi_buy} and MACD bullish", ind)
            return Signal(SignalType.HOLD, 40, f"RSI {r:.1f}, waiting for entry", ind)
        else:
            if r >= self.rsi_sell:
                return Signal(SignalType.SELL, min(50 + (r - self.rsi_sell) * 2, 95),
                              f"RSI {r:.1f} ≥ {self.rsi_sell} — overbought", ind)
            if macd_bearish:
                return Signal(SignalType.SELL, 65, "MACD turned bearish", ind)
            return Signal(SignalType.HOLD, 40, f"RSI {r:.1f}, holding", ind)


# ---------------------------------------------------------------------------
# Mean reversion: Bollinger Band bounce
# ---------------------------------------------------------------------------

class MeanReversionStrategy(Strategy):
    """
    Buys when price dips below the lower Bollinger Band (oversold),
    sells when it reverts to or above the middle band.
    """
    name = "mean_reversion"
    display_name = "Mean Reversion (Bollinger Bands)"
    min_bars = 25

    def __init__(self, period: int = 20, num_std: float = 2.0, **params):
        super().__init__(period=period, num_std=num_std, **params)
        self.period = period
        self.num_std = num_std

    def evaluate(self, bars: list[Bar], has_position: bool) -> Signal:
        closes = [b.close for b in bars]
        upper, mid, lower = bollinger(closes, self.period, self.num_std)
        r = rsi(closes, 14)
        price = closes[-1]
        ind = {"price": price, "bb_upper": upper, "bb_mid": mid, "bb_lower": lower, "rsi": r}

        if lower is None:
            return Signal(SignalType.HOLD, 0, "Insufficient data", ind)

        if not has_position:
            if price <= lower:
                conf = min(60 + (lower - price) / lower * 500, 95)
                return Signal(SignalType.BUY, conf,
                              f"Price ${price:.2f} below lower band ${lower:.2f}", ind)
            return Signal(SignalType.HOLD, 40, "Price within bands", ind)
        else:
            if price >= mid:
                return Signal(SignalType.SELL, 70,
                              f"Price ${price:.2f} reverted to mean ${mid:.2f}", ind)
            return Signal(SignalType.HOLD, 40, "Holding for reversion", ind)


# ---------------------------------------------------------------------------
# Moving-average crossover: golden / death cross
# ---------------------------------------------------------------------------

class MACrossoverStrategy(Strategy):
    """
    Buys on a golden cross (short SMA crosses above long SMA),
    sells on a death cross (short SMA crosses below long SMA).
    """
    name = "ma_crossover"
    display_name = "Moving Average Crossover"
    min_bars = 55

    def __init__(self, fast: int = 20, slow: int = 50, **params):
        super().__init__(fast=fast, slow=slow, **params)
        self.fast = fast
        self.slow = slow

    def evaluate(self, bars: list[Bar], has_position: bool) -> Signal:
        closes = [b.close for b in bars]
        if len(closes) < self.slow + 1:
            return Signal(SignalType.HOLD, 0, "Insufficient data", {})

        fast_now = sma(closes, self.fast)
        slow_now = sma(closes, self.slow)
        fast_prev = sma(closes[:-1], self.fast)
        slow_prev = sma(closes[:-1], self.slow)
        ind = {"sma_fast": fast_now, "sma_slow": slow_now}

        if None in (fast_now, slow_now, fast_prev, slow_prev):
            return Signal(SignalType.HOLD, 0, "Insufficient data", ind)

        golden = fast_prev <= slow_prev and fast_now > slow_now
        death = fast_prev >= slow_prev and fast_now < slow_now

        if not has_position and golden:
            return Signal(SignalType.BUY, 75,
                          f"Golden cross: SMA{self.fast} crossed above SMA{self.slow}", ind)
        if has_position and death:
            return Signal(SignalType.SELL, 75,
                          f"Death cross: SMA{self.fast} crossed below SMA{self.slow}", ind)
        return Signal(SignalType.HOLD, 40, "No crossover", ind)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

STRATEGY_REGISTRY: dict[str, type[Strategy]] = {
    MomentumStrategy.name: MomentumStrategy,
    MeanReversionStrategy.name: MeanReversionStrategy,
    MACrossoverStrategy.name: MACrossoverStrategy,
}


def get_strategy(name: str, **params) -> Strategy:
    cls = STRATEGY_REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGY_REGISTRY)}")
    return cls(**params)


def list_strategies() -> list[dict]:
    return [
        {"name": cls.name, "display_name": cls.display_name, "min_bars": cls.min_bars}
        for cls in STRATEGY_REGISTRY.values()
    ]
