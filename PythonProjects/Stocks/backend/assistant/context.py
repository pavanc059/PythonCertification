"""
build_user_context() — assembles prompt context from the user's actual DB records.

Every fact injected into the LLM system prompt comes from the database.
No hallucination risk on factual questions — the LLM can only describe
what actually happened.
"""

from __future__ import annotations

import logging
from datetime import datetime, date
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def build_user_context(user_id: UUID, question: str, db: Session) -> str:
    """Return a structured context block for the assistant LLM prompt."""
    parts: list[str] = []
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    parts.append("=== Tradewell App — User Context ===")
    parts.append(f"Time: {now_str}")
    parts.append(f"User question: {question}")
    parts.append("")

    # ── 1. Portfolio ─────────────────────────────────────────────────────
    try:
        from sqlalchemy import desc
        from trading.models import PaperTradingAccountDB, PaperPositionDB, PaperOrderDB

        account = db.query(PaperTradingAccountDB).filter_by(user_id=user_id).first()
        if account:
            cash = float(account.cash)
            initial = float(account.initial_cash)
            parts.append("--- PORTFOLIO ---")
            parts.append(f"Cash: ${cash:,.2f}  |  Initial capital: ${initial:,.2f}")
            parts.append(f"Return vs initial (cash only): ${cash - initial:+,.2f}")

            positions = db.query(PaperPositionDB).filter_by(account_id=account.id).all()
            if positions:
                parts.append(f"\nOpen positions ({len(positions)}):")
                for p in positions:
                    entry = float(p.avg_entry_price)
                    cur = float(p.current_price)
                    upnl = (cur - entry) * p.quantity
                    parts.append(f"  {p.ticker}: {p.quantity} shares | entry ${entry:.2f}"
                                  f" | current ${cur:.2f} | unrealized P&L ${upnl:+,.2f}")
            else:
                parts.append("Open positions: none")

            orders = (db.query(PaperOrderDB)
                      .filter_by(account_id=account.id)
                      .order_by(desc(PaperOrderDB.created_at))
                      .limit(5).all())
            if orders:
                parts.append(f"\nLast {len(orders)} orders:")
                for o in orders:
                    ts = o.created_at.strftime("%m-%d %H:%M")
                    fp = f"@ ${float(o.filled_price):.2f}" if o.filled_price else ""
                    parts.append(f"  [{ts}] {o.side.upper()} {o.quantity}x {o.ticker} {fp} — {o.status}")
    except Exception as e:
        logger.debug("portfolio context: %s", e)
    parts.append("")

    # ── 2. Auto-Trade Bots ───────────────────────────────────────────────
    try:
        from sqlalchemy import desc
        from autotrade.models import AutoTradeBotDB, AutoTradeLogDB

        bots = db.query(AutoTradeBotDB).filter_by(user_id=user_id).all()
        if bots:
            parts.append("--- AUTO-TRADE BOTS ---")
            for bot in bots:
                parts.append(
                    f"Bot '{bot.name}' ({'ON' if bot.enabled else 'off'}): "
                    f"{bot.ticker} / {bot.strategy} | "
                    f"trades={bot.total_trades} P&L=${bot.total_pnl:+.2f} | "
                    f"last signal={bot.last_signal or 'none'}"
                )
                if bot.last_error:
                    parts.append(f"  Error: {bot.last_error[:120]}")

            logs = (db.query(AutoTradeLogDB)
                    .filter_by(user_id=user_id)
                    .order_by(desc(AutoTradeLogDB.timestamp))
                    .limit(6).all())
            if logs:
                parts.append(f"\nRecent bot executions:")
                for lg in logs:
                    ts = lg.timestamp.strftime("%m-%d %H:%M")
                    conf = f" ({lg.signal_confidence:.0f}% conf)" if lg.signal_confidence else ""
                    reason_snippet = f" — {lg.signal_reason[:80]}" if lg.signal_reason else ""
                    parts.append(
                        f"  [{ts}] {lg.ticker} signal={lg.signal_type}{conf} "
                        f"action={lg.action_taken}{reason_snippet}"
                    )
    except Exception as e:
        logger.debug("autotrade context: %s", e)
    parts.append("")

    # ── 3. AutoPilot ─────────────────────────────────────────────────────
    try:
        from sqlalchemy import desc
        from autopilot.models import AutoPilotConfigDB, AutoPilotTradeDB

        configs = db.query(AutoPilotConfigDB).filter_by(user_id=user_id).all()
        if configs:
            parts.append("--- AUTOPILOT ---")
            for cfg in configs:
                parts.append(
                    f"{cfg.market_type.capitalize()} AutoPilot ({'ON' if cfg.enabled else 'off'}): "
                    f"target=${cfg.daily_profit_target:.0f}/day | "
                    f"today P&L=${cfg.realized_pnl_today:+.2f} | "
                    f"status={cfg.status}"
                )

            trades = (db.query(AutoPilotTradeDB)
                      .filter_by(user_id=user_id)
                      .order_by(desc(AutoPilotTradeDB.entry_time))
                      .limit(4).all())
            if trades:
                parts.append(f"\nRecent AutoPilot trades:")
                for t in trades:
                    ts = t.entry_time.strftime("%m-%d %H:%M")
                    conf = f" (LLM {t.llm_confidence:.0f}%)" if t.llm_confidence else ""
                    pnl = f" P&L=${t.realized_pnl:+.2f}" if t.realized_pnl is not None else " (open)"
                    reason_snippet = f" | {t.entry_reason[:80]}" if t.entry_reason else ""
                    parts.append(
                        f"  [{ts}] {t.ticker} {t.quantity}sh @ ${t.entry_price:.2f}{conf}"
                        f"{pnl} [{t.status}]{reason_snippet}"
                    )
    except Exception as e:
        logger.debug("autopilot context: %s", e)
    parts.append("")

    # ── 4. Recent activity log ───────────────────────────────────────────
    try:
        from sqlalchemy import desc
        from activity.models import ActivityLogDB

        events = (db.query(ActivityLogDB)
                  .filter_by(user_id=user_id)
                  .order_by(desc(ActivityLogDB.created_at))
                  .limit(8).all())
        if events:
            parts.append("--- RECENT ACTIVITY ---")
            for ev in events:
                ts = ev.created_at.strftime("%m-%d %H:%M")
                parts.append(f"  [{ts}] [{ev.category}] {ev.description}")
    except Exception as e:
        logger.debug("activity context: %s", e)
    parts.append("")

    parts.append("=== End of Context ===")
    return "\n".join(parts)


ASSISTANT_SYSTEM_PROMPT = """You are the Tradewell in-app AI assistant.
You have access to the user's LIVE portfolio data, trade history, bot decisions,
and AutoPilot activity provided above as context.

Your role:
- Answer questions about WHY things happened (why did the portfolio drop, why did a bot buy, what was the analysis)
- Explain bot signals, risk blocks, and AutoPilot logic in plain English
- Summarise performance and P&L
- Be concise and factual — cite the actual data from context
- If something is NOT in the provided context, say so honestly rather than guessing
- Never give real financial advice — always note this is paper trading

Format:
- Use plain text, short paragraphs
- Use bullet points for lists of facts
- Keep responses under 300 words unless the question requires more detail
"""
