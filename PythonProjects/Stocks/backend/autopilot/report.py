"""
End-of-day report generator for AutoPilot.

After the market closes, generate one AutoPilotDailyReportDB row per enabled
config summarising the day: realized P&L versus target, trade stats, best/worst
trade, and an optional LLM-written narrative. Idempotent per (config, day).
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from autopilot.models import (
    AutoPilotConfigDB, AutoPilotTradeDB, AutoPilotDailyReportDB,
)

logger = logging.getLogger(__name__)


class AutoPilotReportGenerator:
    """Builds and persists daily AutoPilot reports."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def generate_for_config(
        self,
        config: AutoPilotConfigDB,
        trading_day: Optional[date] = None,
    ) -> Optional[AutoPilotDailyReportDB]:
        """
        Generate (or refresh) the daily report for one config.

        Returns the report row, or None if there was no activity that day.
        """
        day = trading_day or datetime.utcnow().date()

        trades = (
            self.db.query(AutoPilotTradeDB)
            .filter_by(config_id=config.id, trading_day=day)
            .all()
        )
        closed = [t for t in trades if t.status == "closed" and t.realized_pnl is not None]

        # Nothing happened today — skip (don't clutter history with empty rows)
        if not trades:
            return None

        realized_pnl = round(sum(t.realized_pnl or 0.0 for t in closed), 2)
        num_trades = len(closed)
        winners = [t for t in closed if (t.realized_pnl or 0.0) > 0]
        losers = [t for t in closed if (t.realized_pnl or 0.0) < 0]
        num_winning = len(winners)
        num_losing = len(losers)
        win_rate = round(num_winning / num_trades * 100, 1) if num_trades else 0.0
        best = max((t.realized_pnl for t in closed), default=None)
        worst = min((t.realized_pnl for t in closed), default=None)
        return_pct = round(realized_pnl / config.capital * 100, 2) if config.capital else 0.0
        target_met = realized_pnl >= config.daily_profit_target

        details = json.dumps([
            {
                "ticker": t.ticker,
                "qty": t.quantity,
                "entry": t.entry_price,
                "exit": t.exit_price,
                "pnl": t.realized_pnl,
                "reason": t.exit_reason,
                "llm_confidence": t.llm_confidence,
            }
            for t in closed
        ])

        summary = self._build_summary(
            config, day, realized_pnl, target_met, num_trades,
            num_winning, win_rate, best, worst,
        )

        # Upsert (unique on config_id + trading_day)
        report = (
            self.db.query(AutoPilotDailyReportDB)
            .filter_by(config_id=config.id, trading_day=day)
            .first()
        )
        if report is None:
            report = AutoPilotDailyReportDB(
                config_id=config.id,
                user_id=config.user_id,
                market_type=config.market_type,
                trading_day=day,
            )
            self.db.add(report)

        report.capital = config.capital
        report.daily_profit_target = config.daily_profit_target
        report.realized_pnl = realized_pnl
        report.target_met = target_met
        report.return_pct = return_pct
        report.num_trades = num_trades
        report.num_winning = num_winning
        report.num_losing = num_losing
        report.win_rate = win_rate
        report.best_trade_pnl = best
        report.worst_trade_pnl = worst
        report.summary = summary
        report.details = details

        self.db.commit()
        self.db.refresh(report)
        logger.info(
            "AutoPilot report %s %s: P&L $%.2f (%d trades, %.0f%% win, target %s)",
            config.market_type, day, realized_pnl, num_trades, win_rate,
            "MET" if target_met else "missed",
        )
        return report

    # ------------------------------------------------------------------
    # Narrative
    # ------------------------------------------------------------------

    def _build_summary(
        self, config, day, realized_pnl, target_met, num_trades,
        num_winning, win_rate, best, worst,
    ) -> str:
        """LLM narrative if available, else a deterministic template."""
        base = (
            f"On {day.isoformat()}, the {config.market_type} AutoPilot made "
            f"{num_trades} trade(s) for a realized P&L of ${realized_pnl:.2f} "
            f"against a ${config.daily_profit_target:.0f} target "
            f"({'met' if target_met else 'not met'}). "
            f"Win rate {win_rate:.0f}%"
        )
        if best is not None and worst is not None:
            base += f", best trade ${best:.2f}, worst ${worst:.2f}."
        else:
            base += "."

        # Try an LLM one-liner for color; fall back silently to the template.
        try:
            from autopilot.llm import LLMPredictionGate
            gate = LLMPredictionGate()
            if gate.available:
                resp = gate.client.chat.completions.create(
                    model=gate.model,
                    messages=[
                        {"role": "system", "content": (
                            "You are a trading journal assistant. Write ONE concise, "
                            "factual sentence summarising the day's automated trading "
                            "performance. No hype, no financial advice."
                        )},
                        {"role": "user", "content": base},
                    ],
                    temperature=0.4,
                    max_tokens=120,
                )
                text = (resp.choices[0].message.content or "").strip()
                if text:
                    return text
        except Exception as exc:
            logger.debug("LLM summary unavailable: %s", exc)

        return base


def generate_all_reports(db: Session, trading_day: Optional[date] = None) -> int:
    """Generate reports for every enabled config. Returns count generated."""
    from autopilot.service import get_all_enabled_configs

    gen = AutoPilotReportGenerator(db)
    count = 0
    for config in get_all_enabled_configs(db):
        try:
            if gen.generate_for_config(config, trading_day) is not None:
                count += 1
        except Exception as exc:
            logger.error("Report generation failed for config %s: %s", config.id, exc)
    return count
