"""
AutoPilotService — persistence + orchestration helpers for AutoPilot.

Owns config CRUD (get-or-create per market_type), trade/report queries, and
serialisation to the API response dicts. The executor and Celery tasks reuse
the global helpers at the bottom.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from autopilot.models import (
    AutoPilotConfigDB, AutoPilotTradeDB, AutoPilotDailyReportDB,
)

VALID_MARKET_TYPES = ("penny", "regular")

# Sensible defaults per market type (penny = cheap/volatile, regular = large caps)
_MARKET_DEFAULTS = {
    "penny": dict(
        capital=10000.0, daily_profit_target=100.0, daily_loss_limit=200.0,
        max_concurrent_positions=3, max_position_size_pct=0.34,
        take_profit_pct=0.05, stop_loss_pct=0.03,
        min_price=0.50, max_price=5.0, min_change_pct=5.0,
        min_volume_ratio=2.0, max_candidates=15,
        use_llm=True, llm_min_confidence=60.0,
    ),
    "regular": dict(
        capital=10000.0, daily_profit_target=100.0, daily_loss_limit=200.0,
        max_concurrent_positions=3, max_position_size_pct=0.34,
        take_profit_pct=0.03, stop_loss_pct=0.02,
        min_price=5.0, max_price=1000.0, min_change_pct=2.0,
        min_volume_ratio=1.5, max_candidates=15,
        use_llm=True, llm_min_confidence=60.0,
    ),
}


class AutoPilotService:
    def __init__(self, db: Session, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def get_or_create_config(self, market_type: str) -> AutoPilotConfigDB:
        if market_type not in VALID_MARKET_TYPES:
            raise ValueError(f"Invalid market_type '{market_type}'")

        config = (
            self.db.query(AutoPilotConfigDB)
            .filter_by(user_id=self.user_id, market_type=market_type)
            .first()
        )
        if config is None:
            config = AutoPilotConfigDB(
                user_id=self.user_id,
                market_type=market_type,
                enabled=False,
                **_MARKET_DEFAULTS[market_type],
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
        return config

    def update_config(self, market_type: str, updates: dict) -> AutoPilotConfigDB:
        config = self.get_or_create_config(market_type)
        for key, value in updates.items():
            if value is not None and hasattr(config, key):
                setattr(config, key, value)
        self.db.commit()
        self.db.refresh(config)
        return config

    # ------------------------------------------------------------------
    # Trades & reports
    # ------------------------------------------------------------------

    def get_open_trades(self, market_type: str) -> List[AutoPilotTradeDB]:
        config = self.get_or_create_config(market_type)
        return (
            self.db.query(AutoPilotTradeDB)
            .filter_by(config_id=config.id, status="open")
            .order_by(AutoPilotTradeDB.entry_time.desc())
            .all()
        )

    def get_trades(self, market_type: str, limit: int = 100) -> List[AutoPilotTradeDB]:
        config = self.get_or_create_config(market_type)
        return (
            self.db.query(AutoPilotTradeDB)
            .filter_by(config_id=config.id)
            .order_by(AutoPilotTradeDB.entry_time.desc())
            .limit(limit)
            .all()
        )

    def get_reports(self, market_type: str, limit: int = 60) -> List[AutoPilotDailyReportDB]:
        config = self.get_or_create_config(market_type)
        return (
            self.db.query(AutoPilotDailyReportDB)
            .filter_by(config_id=config.id)
            .order_by(AutoPilotDailyReportDB.trading_day.desc())
            .limit(limit)
            .all()
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    @staticmethod
    def config_to_dict(c: AutoPilotConfigDB) -> dict:
        return {
            "id": str(c.id),
            "market_type": c.market_type,
            "enabled": c.enabled,
            "capital": c.capital,
            "daily_profit_target": c.daily_profit_target,
            "daily_loss_limit": c.daily_loss_limit,
            "max_concurrent_positions": c.max_concurrent_positions,
            "max_position_size_pct": c.max_position_size_pct,
            "take_profit_pct": c.take_profit_pct,
            "stop_loss_pct": c.stop_loss_pct,
            "min_price": c.min_price,
            "max_price": c.max_price,
            "min_change_pct": c.min_change_pct,
            "min_volume_ratio": c.min_volume_ratio,
            "max_candidates": c.max_candidates,
            "use_llm": c.use_llm,
            "llm_min_confidence": c.llm_min_confidence,
            "force_flat_minutes_before_close": c.force_flat_minutes_before_close,
            "data_provider": c.data_provider,
            "trading_day": c.trading_day.isoformat() if c.trading_day else None,
            "realized_pnl_today": c.realized_pnl_today,
            "trades_today": c.trades_today,
            "target_hit": c.target_hit,
            "halted": c.halted,
            "status": c.status,
            "last_run_at": c.last_run_at.isoformat() if c.last_run_at else None,
            "last_error": c.last_error,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }

    def status_dict(self, market_type: str) -> dict:
        c = self.get_or_create_config(market_type)
        open_positions = (
            self.db.query(AutoPilotTradeDB)
            .filter_by(config_id=c.id, status="open")
            .count()
        )
        progress = (c.realized_pnl_today / c.daily_profit_target * 100) if c.daily_profit_target else 0.0
        return {
            "market_type": c.market_type,
            "enabled": c.enabled,
            "status": c.status,
            "capital": c.capital,
            "daily_profit_target": c.daily_profit_target,
            "realized_pnl_today": c.realized_pnl_today,
            "progress_pct": round(max(progress, 0.0), 1),
            "target_hit": c.target_hit,
            "halted": c.halted,
            "trades_today": c.trades_today,
            "open_positions": open_positions,
            "last_run_at": c.last_run_at.isoformat() if c.last_run_at else None,
        }

    @staticmethod
    def trade_to_dict(t: AutoPilotTradeDB) -> dict:
        return {
            "id": str(t.id),
            "market_type": t.market_type,
            "ticker": t.ticker,
            "trading_day": t.trading_day.isoformat(),
            "entry_time": t.entry_time.isoformat(),
            "entry_price": t.entry_price,
            "quantity": t.quantity,
            "stop_price": t.stop_price,
            "take_profit_price": t.take_profit_price,
            "momentum_score": t.momentum_score,
            "llm_confidence": t.llm_confidence,
            "entry_reason": t.entry_reason,
            "status": t.status,
            "exit_time": t.exit_time.isoformat() if t.exit_time else None,
            "exit_price": t.exit_price,
            "exit_reason": t.exit_reason,
            "realized_pnl": t.realized_pnl,
            "realized_pnl_pct": t.realized_pnl_pct,
        }

    @staticmethod
    def report_to_dict(r: AutoPilotDailyReportDB) -> dict:
        return {
            "id": str(r.id),
            "market_type": r.market_type,
            "trading_day": r.trading_day.isoformat(),
            "capital": r.capital,
            "daily_profit_target": r.daily_profit_target,
            "realized_pnl": r.realized_pnl,
            "target_met": r.target_met,
            "return_pct": r.return_pct,
            "num_trades": r.num_trades,
            "num_winning": r.num_winning,
            "num_losing": r.num_losing,
            "win_rate": r.win_rate,
            "best_trade_pnl": r.best_trade_pnl,
            "worst_trade_pnl": r.worst_trade_pnl,
            "summary": r.summary,
        }


# ---------------------------------------------------------------------------
# Global helpers (Celery tasks — no user scoping)
# ---------------------------------------------------------------------------

def get_all_enabled_configs(db: Session) -> List[AutoPilotConfigDB]:
    """All enabled AutoPilot configs across every user."""
    return db.query(AutoPilotConfigDB).filter_by(enabled=True).all()


def get_config_by_id(db: Session, config_id: UUID) -> Optional[AutoPilotConfigDB]:
    return db.query(AutoPilotConfigDB).filter_by(id=config_id).first()
