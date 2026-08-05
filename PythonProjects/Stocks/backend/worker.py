"""
Backend-side Celery app for trading-domain background tasks.

Why a separate Celery app?
--------------------------
The main ``stockiq.infrastructure.tasks`` worker runs on the root image, which
does NOT have the backend application modules (``database``, ``autopilot``,
``trading`` …) or their dependencies (``openai`` …) on its path. The trading
tasks below need those modules, so they run here — on the *backend* image,
which has the full FastAPI app, models, and dependencies available.

Run with:
    celery -A worker worker --loglevel=info --concurrency=2
    celery -A worker beat   --loglevel=info

Both share the same Redis broker as the stockiq worker but use dedicated
task names, so there is no overlap.

All trading is PAPER ONLY.
"""

from __future__ import annotations

import logging
import os

from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Register ALL ORM models so SQLAlchemy can resolve string-based relationships
# (e.g. AutoPilotConfigDB.user -> "User"). Unlike the FastAPI app, this worker
# never imports the routers, so we must import the model modules explicitly
# before any query triggers mapper configuration.
# ---------------------------------------------------------------------------
import auth.models  # noqa: F401,E402  (defines User)
import trading.models  # noqa: F401,E402  (paper trading tables)
import autotrade.models  # noqa: F401,E402
import autopilot.models  # noqa: F401,E402

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")

celery_app = Celery("stockiq_trading", broker=BROKER_URL, backend=RESULT_BACKEND)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,       # 10 min hard limit per task
    task_soft_time_limit=540,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        # AutoPilot: scan + trade every 5 minutes during market hours (ET ~ 13-20 UTC)
        "run-autopilot": {
            "task": "worker.run_autopilot",
            "schedule": crontab(minute="*/5", hour="9-15", day_of_week="mon-fri"),
        },
        # AutoPilot: force-flat all positions at 15:55 ET (no overnight risk)
        "autopilot-force-flat": {
            "task": "worker.autopilot_force_flat",
            "schedule": crontab(minute=55, hour=15, day_of_week="mon-fri"),
        },
        # AutoPilot: end-of-day report at 16:15 ET
        "autopilot-eod-report": {
            "task": "worker.autopilot_eod_report",
            "schedule": crontab(minute=15, hour=16, day_of_week="mon-fri"),
        },
        # Per-ticker Auto-Trade bots every 5 minutes during market hours
        "run-autotrade-bots": {
            "task": "worker.run_autotrade_bots",
            "schedule": crontab(minute="*/5", hour="9-16", day_of_week="mon-fri"),
        },
        # Daily AI predictions pre-warm at 07:00 ET (Mon–Fri, before market open)
        # Computes fresh RSI/MACD/SMA + LLM enrichment for the default watchlist
        # and stores results in Redis under "predictions:daily:v2" for 24 hours.
        # This ensures the /market/predictions endpoint is instant during the day.
        "refresh-daily-predictions": {
            "task": "worker.refresh_daily_predictions",
            "schedule": crontab(hour=7, minute=0, day_of_week="mon-fri"),
        },
        # News cache warm-up every 15 minutes (so users never wait for a cold fetch)
        "refresh-market-news": {
            "task": "worker.refresh_market_news",
            "schedule": crontab(minute="*/15"),
        },
        # Penny stocks cache refresh every 5 minutes during market hours
        "refresh-penny-stocks": {
            "task": "worker.refresh_penny_stocks",
            "schedule": crontab(minute="*/5", hour="9-16", day_of_week="mon-fri"),
        },
        # Movers cache refresh every 5 minutes during market hours
        "refresh-movers": {
            "task": "worker.refresh_movers",
            "schedule": crontab(minute="*/5", hour="9-16", day_of_week="mon-fri"),
        },
    },
)


# ---------------------------------------------------------------------------
# AutoPilot tasks
# ---------------------------------------------------------------------------

@celery_app.task(name="worker.run_autopilot", bind=True, max_retries=0)
def run_autopilot(self):
    """Execute every enabled AutoPilot config (penny + regular, all users)."""
    logger.info("task_started run_autopilot")
    from database import SessionLocal
    from autopilot.service import get_all_enabled_configs
    from autopilot.executor import AutoPilotExecutor

    db = SessionLocal()
    try:
        configs = get_all_enabled_configs(db)
        if not configs:
            return {"configs_run": 0}
        executor = AutoPilotExecutor(db)
        success = 0
        for config in configs:
            try:
                executor.run(config.id)
                success += 1
            except Exception as exc:
                logger.error("autopilot_run_failed config=%s: %s", config.id, exc)
        return {"configs_run": success, "total": len(configs)}
    except Exception as exc:
        logger.exception("run_autopilot failed: %s", exc)
        return {"error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="worker.autopilot_force_flat", bind=True, max_retries=0)
def autopilot_force_flat(self):
    """Force-close all open AutoPilot positions before market close."""
    logger.info("task_started autopilot_force_flat")
    from database import SessionLocal
    from autopilot.service import get_all_enabled_configs
    from autopilot.executor import AutoPilotExecutor

    db = SessionLocal()
    try:
        configs = get_all_enabled_configs(db)
        executor = AutoPilotExecutor(db)
        flattened = 0
        for config in configs:
            try:
                executor.force_flat(config.id, reason="force_flat")
                flattened += 1
            except Exception as exc:
                logger.error("autopilot_flat_failed config=%s: %s", config.id, exc)
        return {"flattened": flattened}
    except Exception as exc:
        logger.exception("autopilot_force_flat failed: %s", exc)
        return {"error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="worker.autopilot_eod_report", bind=True, max_retries=2, default_retry_delay=120)
def autopilot_eod_report(self):
    """Generate end-of-day AutoPilot reports for all enabled configs."""
    logger.info("task_started autopilot_eod_report")
    from database import SessionLocal
    from autopilot.report import generate_all_reports

    db = SessionLocal()
    try:
        count = generate_all_reports(db)
        return {"reports_generated": count}
    except Exception as exc:
        logger.exception("autopilot_eod_report failed: %s", exc)
        return {"error": str(exc)}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Per-ticker Auto-Trade bots
# ---------------------------------------------------------------------------

@celery_app.task(name="worker.run_autotrade_bots", bind=True, max_retries=0)
def run_autotrade_bots(self):
    """Execute all enabled per-ticker Auto-Trade bots."""
    logger.info("task_started run_autotrade_bots")
    from database import SessionLocal
    from autotrade.service import get_all_enabled_bots
    from autotrade.executor import BotExecutor

    db = SessionLocal()
    try:
        bots = get_all_enabled_bots(db)
        if not bots:
            return {"bots_run": 0}
        executor = BotExecutor(db)
        success = 0
        for bot in bots:
            try:
                executor.run_bot(bot.id)
                success += 1
            except Exception as exc:
                logger.error("bot_execution_failed bot=%s: %s", bot.id, exc)
        return {"bots_run": success, "total": len(bots)}
    except Exception as exc:
        logger.exception("run_autotrade_bots failed: %s", exc)
        return {"error": str(exc)}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Market data refresh tasks
# ---------------------------------------------------------------------------

# Default watchlist for daily prediction pre-warm.
# These 20 tickers are always computed regardless of user watchlists.
# They cover the most-watched large/mid caps + a few volatile names.
_PREDICTION_WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA",
    "AMD", "INTC", "NFLX", "JPM", "BAC", "AVGO", "CRM", "ORCL",
    "PYPL", "MU", "QCOM", "PLTR", "UBER",
]


def _get_market_service():
    """
    Build a WebullMarketService instance using the backend config + Redis.

    The service is created fresh each task invocation so we never share
    Redis connections across forked worker processes.
    """
    import os
    from market.service import WebullMarketService

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    data_source = os.getenv("MARKET_DATA_SOURCE", "yfinance")
    return WebullMarketService(redis_url=redis_url, data_source=data_source)


@celery_app.task(
    name="worker.refresh_daily_predictions",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    time_limit=480,          # 8 min: 20 tickers × ~15s each (with LLM) = ~5 min
    soft_time_limit=420,
)
def refresh_daily_predictions(self):
    """
    Pre-warm the daily AI predictions cache for the default watchlist.

    Runs at 07:00 ET Mon–Fri (before market open). For each ticker:
      1. Fetch 1-year daily bars from yfinance
      2. Compute RSI / MACD / SMA-cross / 30d momentum
      3. Enrich with news sentiment + LLM confidence adjustment
      4. Store individual ticker result under "pred:v2:{ticker}" (15 min TTL)

    Then writes the full list to "predictions:daily:v2" with a 26-hour TTL
    so any request during the trading day gets an instant cache hit.

    Returns {"refreshed": int, "failed": int, "tickers": [...]}
    """
    logger.info("task_started refresh_daily_predictions")
    try:
        service = _get_market_service()
        refreshed = []
        failed = []

        for ticker in _PREDICTION_WATCHLIST:
            try:
                # Force a fresh compute by busting the per-ticker cache first
                if service._redis:
                    service._redis.delete(f"pred:v2:{ticker}")

                pred = service._compute_prediction(ticker)
                if pred:
                    refreshed.append(ticker)
                    logger.info("prediction_refreshed ticker=%s category=%s", ticker, pred["category"])
                else:
                    failed.append(ticker)
                    logger.warning("prediction_failed ticker=%s (returned None)", ticker)
            except Exception as exc:
                failed.append(ticker)
                logger.error("prediction_error ticker=%s error=%s", ticker, exc)

        # Build the daily aggregated list and cache for 26 hours
        all_preds = []
        for ticker in _PREDICTION_WATCHLIST:
            cached = service._cache_get(f"pred:v2:{ticker}")
            if cached:
                all_preds.append(cached)

        if all_preds:
            # Sort: Strong Buy → Buy → Hold → Sell → Strong Sell
            order = {"Strong Buy": 0, "Buy": 1, "Hold": 2, "Sell": 3, "Strong Sell": 4}
            all_preds.sort(key=lambda p: order.get(p.get("category", "Hold"), 2))
            service._cache_set("predictions:daily:v2", all_preds, ttl=93600)  # 26 hours
            logger.info(
                "daily_predictions_cached count=%d refreshed=%d failed=%d",
                len(all_preds), len(refreshed), len(failed),
            )

        return {"refreshed": len(refreshed), "failed": len(failed), "tickers": refreshed}

    except Exception as exc:
        logger.exception("refresh_daily_predictions failed: %s", exc)
        return {"error": str(exc)}


@celery_app.task(
    name="worker.refresh_market_news",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    time_limit=90,
    soft_time_limit=75,
)
def refresh_market_news(self):
    """
    Warm the general market news cache every 15 minutes.

    Fetches the latest 20 headlines through the Finnhub → NewsAPI → yfinance
    chain and stores them in Redis so the /market/news endpoint never cold-
    fetches on a user request.

    The cache keys it warms:
      - "news:v2:all::::0:20"   (first 20 headlines, no filters)
    """
    logger.info("task_started refresh_market_news")
    try:
        service = _get_market_service()

        # Bust the general news cache so get_news() re-fetches from APIs
        if service._redis:
            # Clear all general news cache keys (offset 0, limit 20)
            for key in service._redis.scan_iter("news:v2:all:*"):
                service._redis.delete(key)

        # Re-fetch and re-cache
        articles = service.get_news(limit=20, offset=0)
        logger.info("news_refreshed count=%d", len(articles))
        return {"articles_fetched": len(articles)}

    except Exception as exc:
        logger.exception("refresh_market_news failed: %s", exc)
        return {"error": str(exc)}


@celery_app.task(
    name="worker.refresh_movers",
    bind=True,
    max_retries=0,
    time_limit=120,
    soft_time_limit=100,
)
def refresh_movers(self):
    """
    Refresh the top gainers / losers cache every 5 minutes during market hours.

    Busts the "movers:v2" key so get_movers() re-scans the 40-ticker watchlist
    via yfinance on the next cache miss, then immediately warms it.
    """
    logger.info("task_started refresh_movers")
    try:
        service = _get_market_service()

        # Bust stale cache
        if service._redis:
            service._redis.delete("movers:v2")

        movers = service.get_movers()
        gainers = len(movers.get("gainers", []))
        losers = len(movers.get("losers", []))
        logger.info(
            "movers_refreshed gainers=%d losers=%d source=%s",
            gainers, losers, movers.get("data_source", "?"),
        )
        return {"gainers": gainers, "losers": losers}

    except Exception as exc:
        logger.exception("refresh_movers failed: %s", exc)
        return {"error": str(exc)}


@celery_app.task(
    name="worker.refresh_penny_stocks",
    bind=True,
    max_retries=0,
    time_limit=360,
    soft_time_limit=300,
)
def refresh_penny_stocks(self):
    """
    Scan and pre-warm the live penny stocks cache every 5 minutes during market hours.

    Busts "penny_stocks:live:v2" then calls get_penny_stocks() which scans
    the 30-ticker universe via yfinance, computes momentum / suspicion / risk,
    fetches news catalysts, and caches results for 5 minutes.
    """
    logger.info("task_started refresh_penny_stocks")
    try:
        service = _get_market_service()
        if service._redis:
            service._redis.delete("penny_stocks:live:v2")
        stocks = service.get_penny_stocks()
        logger.info("penny_stocks_refreshed count=%d", len(stocks))
        return {"stocks": len(stocks)}
    except Exception as exc:
        logger.exception("refresh_penny_stocks failed: %s", exc)
        return {"error": str(exc)}
