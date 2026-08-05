"""
Backtester for the auto-trade engine.

Replays a strategy bar-by-bar over historical OHLCV data, driving the same
RiskManager the live paper-trader uses. This is intentionally a single-ticker
event loop: on each bar it first checks stop-loss / take-profit on any open
position, then asks the strategy for a signal, then applies risk gates before
opening a new position.

Realism notes:
- Fills use the bar's close (entries) with a configurable slippage/commission.
- Stops/targets are checked against the bar's low/high, worst-case first.
- No look-ahead: the strategy only ever sees bars up to and including the
  current one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from autotrade.strategies import Strategy, Bar, SignalType
from autotrade.risk import RiskManager, RiskConfig


COMMISSION_PER_TRADE = 0.0     # paper broker is commission-free
SLIPPAGE_PCT = 0.0005          # 5 bps slippage on fills


@dataclass
class Trade:
    ticker: str
    entry_time: str
    entry_price: float
    exit_time: str
    exit_price: float
    quantity: int
    realized_pnl: float
    realized_pnl_pct: float
    exit_reason: str           # "signal" | "stop_loss" | "take_profit" | "end_of_data"


@dataclass
class OpenPosition:
    entry_time: str
    entry_price: float
    quantity: int
    stop_price: float
    take_profit_price: float


@dataclass
class BacktestResult:
    ticker: str
    strategy: str
    start_date: str
    end_date: str
    initial_capital: float
    final_equity: float
    total_return: float
    total_return_pct: float
    num_trades: int
    num_winning: int
    num_losing: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: float
    trades: list[dict]
    equity_curve: list[dict]   # [{date, equity}]


def _parse_date(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return datetime.utcnow()


class Backtester:
    def __init__(self, strategy: Strategy, risk_config: RiskConfig,
                 initial_capital: float = 100_000.0) -> None:
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.risk = RiskManager(risk_config)

    def run(self, ticker: str, bars: list[Bar]) -> BacktestResult:
        cash = self.initial_capital
        position: Optional[OpenPosition] = None
        trades: list[Trade] = []
        equity_curve: list[dict] = []
        daily_returns: list[float] = []
        peak_equity = self.initial_capital
        max_drawdown = 0.0
        prev_equity = self.initial_capital

        min_bars = self.strategy.min_bars

        for i in range(len(bars)):
            bar = bars[i]
            window = bars[: i + 1]
            bar_date = _parse_date(bar.timestamp).date()

            # Mark-to-market equity
            pos_value = position.quantity * bar.close if position else 0.0
            equity = cash + pos_value

            # --- 1. Stop-loss / take-profit on open position ---
            if position is not None:
                exit_reason = self.risk.check_stops(
                    entry_price=position.entry_price,
                    current_low=bar.low,
                    current_high=bar.high,
                    stop_price=position.stop_price,
                    take_profit_price=position.take_profit_price,
                )
                if exit_reason:
                    fill = position.stop_price if exit_reason == "stop_loss" else position.take_profit_price
                    fill *= (1 - SLIPPAGE_PCT)  # slippage against us
                    proceeds = fill * position.quantity - COMMISSION_PER_TRADE
                    cost = position.entry_price * position.quantity
                    pnl = proceeds - cost
                    cash += proceeds
                    self.risk.record_trade_close(pnl)
                    trades.append(Trade(
                        ticker=ticker,
                        entry_time=position.entry_time,
                        entry_price=position.entry_price,
                        exit_time=bar.timestamp,
                        exit_price=round(fill, 2),
                        quantity=position.quantity,
                        realized_pnl=round(pnl, 2),
                        realized_pnl_pct=round(pnl / cost * 100, 2) if cost else 0.0,
                        exit_reason=exit_reason,
                    ))
                    position = None

            # --- 2. Strategy signal ---
            if i + 1 >= min_bars:
                signal = self.strategy.evaluate(window, has_position=position is not None)

                # Exit on SELL signal
                if position is not None and signal.type == SignalType.SELL:
                    fill = bar.close * (1 - SLIPPAGE_PCT)
                    proceeds = fill * position.quantity - COMMISSION_PER_TRADE
                    cost = position.entry_price * position.quantity
                    pnl = proceeds - cost
                    cash += proceeds
                    self.risk.record_trade_close(pnl)
                    trades.append(Trade(
                        ticker=ticker,
                        entry_time=position.entry_time,
                        entry_price=position.entry_price,
                        exit_time=bar.timestamp,
                        exit_price=round(fill, 2),
                        quantity=position.quantity,
                        realized_pnl=round(pnl, 2),
                        realized_pnl_pct=round(pnl / cost * 100, 2) if cost else 0.0,
                        exit_reason="signal",
                    ))
                    position = None

                # Enter on BUY signal
                elif position is None and signal.type == SignalType.BUY:
                    decision = self.risk.evaluate_entry(
                        today=bar_date,
                        equity=equity,
                        cash=cash,
                        price=bar.close,
                        confidence=signal.confidence,
                        open_positions=0,  # single-ticker backtest
                    )
                    if decision.approved:
                        fill = bar.close * (1 + SLIPPAGE_PCT)  # slippage against us
                        cost = fill * decision.quantity + COMMISSION_PER_TRADE
                        if cost <= cash:
                            cash -= cost
                            position = OpenPosition(
                                entry_time=bar.timestamp,
                                entry_price=round(fill, 2),
                                quantity=decision.quantity,
                                stop_price=decision.stop_price,
                                take_profit_price=decision.take_profit_price,
                            )
                            self.risk.record_trade_open()

            # --- 3. Record equity point ---
            pos_value = position.quantity * bar.close if position else 0.0
            equity = cash + pos_value
            equity_curve.append({"date": bar.timestamp[:10], "equity": round(equity, 2)})

            # Drawdown tracking
            peak_equity = max(peak_equity, equity)
            dd = (peak_equity - equity) / peak_equity if peak_equity else 0.0
            max_drawdown = max(max_drawdown, dd)

            # Daily return for Sharpe
            if prev_equity > 0:
                daily_returns.append((equity - prev_equity) / prev_equity)
            prev_equity = equity

        # --- Close any position at end of data ---
        if position is not None:
            last = bars[-1]
            fill = last.close * (1 - SLIPPAGE_PCT)
            proceeds = fill * position.quantity
            cost = position.entry_price * position.quantity
            pnl = proceeds - cost
            cash += proceeds
            trades.append(Trade(
                ticker=ticker,
                entry_time=position.entry_time,
                entry_price=position.entry_price,
                exit_time=last.timestamp,
                exit_price=round(fill, 2),
                quantity=position.quantity,
                realized_pnl=round(pnl, 2),
                realized_pnl_pct=round(pnl / cost * 100, 2) if cost else 0.0,
                exit_reason="end_of_data",
            ))
            position = None

        final_equity = cash

        return self._compute_metrics(
            ticker=ticker, bars=bars, trades=trades,
            equity_curve=equity_curve, daily_returns=daily_returns,
            final_equity=final_equity, max_drawdown=max_drawdown,
        )

    def _compute_metrics(self, *, ticker, bars, trades, equity_curve,
                         daily_returns, final_equity, max_drawdown) -> BacktestResult:
        wins = [t for t in trades if t.realized_pnl > 0]
        losses = [t for t in trades if t.realized_pnl <= 0]
        num_trades = len(trades)
        win_rate = len(wins) / num_trades * 100 if num_trades else 0.0
        avg_win = sum(t.realized_pnl for t in wins) / len(wins) if wins else 0.0
        avg_loss = sum(t.realized_pnl for t in losses) / len(losses) if losses else 0.0
        gross_profit = sum(t.realized_pnl for t in wins)
        gross_loss = abs(sum(t.realized_pnl for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss else (gross_profit if gross_profit else 0.0)

        total_return = final_equity - self.initial_capital
        total_return_pct = total_return / self.initial_capital * 100 if self.initial_capital else 0.0

        # Annualised Sharpe (daily bars → 252 trading days)
        sharpe = 0.0
        if len(daily_returns) > 1:
            mean_r = sum(daily_returns) / len(daily_returns)
            var = sum((r - mean_r) ** 2 for r in daily_returns) / len(daily_returns)
            std = var ** 0.5
            if std > 0:
                sharpe = (mean_r / std) * (252 ** 0.5)

        return BacktestResult(
            ticker=ticker,
            strategy=self.strategy.name,
            start_date=bars[0].timestamp[:10] if bars else "",
            end_date=bars[-1].timestamp[:10] if bars else "",
            initial_capital=self.initial_capital,
            final_equity=round(final_equity, 2),
            total_return=round(total_return, 2),
            total_return_pct=round(total_return_pct, 2),
            num_trades=num_trades,
            num_winning=len(wins),
            num_losing=len(losses),
            win_rate=round(win_rate, 1),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            profit_factor=round(profit_factor, 2),
            max_drawdown_pct=round(max_drawdown * 100, 2),
            sharpe_ratio=round(sharpe, 2),
            trades=[t.__dict__ for t in trades],
            equity_curve=equity_curve,
        )
