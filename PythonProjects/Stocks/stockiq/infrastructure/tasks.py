"""
Celery task queue configuration and task definitions.

This module sets up Celery for asynchronous task processing with Redis as the
message broker and result backend. Tasks are organized into different queues
based on their function (data collection, ML processing, alerts).

Requirements:
- 23.1: Asynchronous task processing using Celery
- 23.2: Process ML model training tasks asynchronously
- 23.3: Process backtest simulations asynchronously with progress tracking
- 23.4: Process bulk data collection tasks asynchronously
"""

from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange
import structlog

from .config import get_settings

logger = structlog.get_logger(__name__)

# Get settings
settings = get_settings()

# Create Celery application instance
celery_app = Celery(
    "stockiq",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "stockiq.infrastructure.tasks",
    ],
)

# Celery Configuration
celery_app.conf.update(
    # Task Configuration
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task Execution
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minutes soft limit
    task_acks_late=True,  # Acknowledge task after execution
    task_reject_on_worker_lost=True,
    
    # Task Result Backend
    result_expires=86400,  # Results expire after 24 hours
    result_backend_transport_options={
        "master_name": "mymaster",
        "retry_on_timeout": True,
    },
    
    # Worker Configuration
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks to prevent memory leaks
    worker_disable_rate_limits=False,
    
    # Broker Configuration
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # Task Retry Configuration
    task_autoretry_for=(Exception,),
    task_retry_kwargs={"max_retries": 3},
    task_retry_backoff=True,  # Exponential backoff
    task_retry_backoff_max=600,  # Max 10 minutes between retries
    task_retry_jitter=True,  # Add random jitter to prevent thundering herd
    
    # Task Routing
    task_routes={
        "stockiq.infrastructure.tasks.collect_market_data": {"queue": "data"},
        "stockiq.infrastructure.tasks.collect_latest_news": {"queue": "data"},
        "stockiq.infrastructure.tasks.collect_news_articles": {"queue": "data"},
        "stockiq.infrastructure.tasks.process_news": {"queue": "data"},
        "stockiq.infrastructure.tasks.process_news_sentiment": {"queue": "data"},
        "stockiq.infrastructure.tasks.analyze_news_sentiment": {"queue": "data"},
        "stockiq.infrastructure.tasks.scan_top_movers": {"queue": "data"},
        "stockiq.infrastructure.tasks.calculate_top_movers": {"queue": "data"},
        "stockiq.infrastructure.tasks.scan_penny_stocks": {"queue": "data"},
        "stockiq.infrastructure.tasks.calculate_technical_indicators": {"queue": "data"},
        "stockiq.infrastructure.tasks.train_ml_model": {"queue": "ml"},
        "stockiq.infrastructure.tasks.run_backtest": {"queue": "ml"},
        "stockiq.infrastructure.tasks.generate_daily_predictions": {"queue": "ml"},
        "stockiq.infrastructure.tasks.track_model_performance": {"queue": "ml"},
        "stockiq.infrastructure.tasks.send_alert": {"queue": "alerts"},
        "stockiq.infrastructure.tasks.send_daily_reports": {"queue": "alerts"},
        "stockiq.infrastructure.tasks.send_daily_report": {"queue": "alerts"},
    },
    
    # Task Priority (0-9, higher = more priority)
    task_default_priority=5,
    task_queue_max_priority=10,
    
    # Beat Schedule Configuration
    beat_schedule={
        # News collection every 30 minutes
        "collect-news-every-30-minutes": {
            "task": "stockiq.infrastructure.tasks.collect_latest_news",
            "schedule": crontab(minute="*/30"),
            "options": {"queue": "data", "priority": 7},
        },
        # Market data collection every 5 minutes during market hours (9:30 AM - 4:00 PM ET)
        "collect-market-data-every-5-minutes": {
            "task": "stockiq.infrastructure.tasks.collect_market_data",
            "schedule": crontab(minute="*/5", hour="9-16", day_of_week="mon-fri"),
            "options": {"queue": "data", "priority": 8},
        },
        # Top movers scan every 5 minutes during market hours
        "scan-top-movers-every-5-minutes": {
            "task": "stockiq.infrastructure.tasks.scan_top_movers",
            "schedule": crontab(minute="*/5", hour="9-16", day_of_week="mon-fri"),
            "options": {"queue": "data", "priority": 7},
        },
        # Penny stock scan every 2 minutes during market hours
        "scan-penny-stocks-every-2-minutes": {
            "task": "stockiq.infrastructure.tasks.scan_penny_stocks",
            "schedule": crontab(minute="*/2", hour="9-16", day_of_week="mon-fri"),
            "options": {"queue": "data", "priority": 6},
        },
        # Daily predictions generation at 7:00 AM ET (before market open)
        "generate-daily-predictions": {
            "task": "stockiq.infrastructure.tasks.generate_daily_predictions",
            "schedule": crontab(hour=7, minute=0, day_of_week="mon-fri"),
            "options": {"queue": "ml", "priority": 9},
        },
        # Daily report generation at 8:00 AM ET
        "send-daily-reports": {
            "task": "stockiq.infrastructure.tasks.send_daily_reports",
            "schedule": crontab(hour=8, minute=0, day_of_week="mon-fri"),
            "options": {"queue": "alerts", "priority": 8},
        },
        # News sentiment analysis every 15 minutes
        "analyze-news-sentiment": {
            "task": "stockiq.infrastructure.tasks.analyze_news_sentiment",
            "schedule": crontab(minute="*/15"),
            "options": {"queue": "data", "priority": 6},
        },
        # Model performance tracking daily at 5:00 PM ET (after market close)
        "track-model-performance": {
            "task": "stockiq.infrastructure.tasks.track_model_performance",
            "schedule": crontab(hour=17, minute=0, day_of_week="mon-fri"),
            "options": {"queue": "ml", "priority": 5},
        },
        # NOTE: Trading-domain tasks (run-autotrade-bots, run-autopilot,
        # autopilot-force-flat, autopilot-eod-report) run on the dedicated
        # BACKEND Celery app (backend/worker.py), not here — this worker's
        # image lacks the backend modules/deps those tasks require.
    },
)

# Define task queues with priority support
celery_app.conf.task_queues = (
    Queue(
        "data",
        Exchange("data", type="direct"),
        routing_key="data",
        priority=10,
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "ml",
        Exchange("ml", type="direct"),
        routing_key="ml",
        priority=10,
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "alerts",
        Exchange("alerts", type="direct"),
        routing_key="alerts",
        priority=10,
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "celery",  # Default queue
        Exchange("celery", type="direct"),
        routing_key="celery",
        priority=5,
        queue_arguments={"x-max-priority": 10},
    ),
)


# ============================================================================
# Task Definitions
# ============================================================================


@celery_app.task(
    name="stockiq.infrastructure.tasks.collect_market_data",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def collect_market_data(self, tickers=None):
    """
    Collect market data for specified tickers or all tracked tickers.
    
    Args:
        tickers: List of ticker symbols or None for all tracked tickers
        
    Returns:
        dict: Collection results with counts and errors
        
    Requirement: 23.4 - Process bulk data collection tasks asynchronously
    """
    logger.info("task_started", task="collect_market_data", tickers=tickers)
    
    try:
        # Import here to avoid circular dependencies
        from stockiq.data.collectors.market import MarketDataCollector
        
        collector = MarketDataCollector()
        
        if tickers is None:
            # TODO: Get tickers from watchlist or default list
            tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        
        results = {
            "success": 0,
            "failed": 0,
            "errors": []
        }
        
        for ticker in tickers:
            try:
                # Collect data (implementation depends on MarketDataCollector)
                # collector.collect_historical_data(ticker)
                results["success"] += 1
                logger.info("ticker_data_collected", ticker=ticker)
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"ticker": ticker, "error": str(e)})
                logger.error("ticker_data_collection_failed", ticker=ticker, error=str(e))
        
        logger.info("task_completed", task="collect_market_data", results=results)
        return results
        
    except Exception as exc:
        logger.error("task_failed", task="collect_market_data", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.collect_latest_news",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def collect_latest_news(self, limit=100):
    """
    Collect latest news from all configured sources.
    
    Args:
        limit: Maximum number of news articles to collect
        
    Returns:
        dict: Collection results with article count
        
    Requirement: 23.4 - Process bulk data collection tasks asynchronously
    """
    logger.info("task_started", task="collect_latest_news", limit=limit)
    
    try:
        # TODO: Implement news collection
        # This will be implemented in Phase 0.2
        results = {
            "articles_collected": 0,
            "sources": [],
            "errors": []
        }
        
        logger.info("task_completed", task="collect_latest_news", results=results)
        return results
        
    except Exception as exc:
        logger.error("task_failed", task="collect_latest_news", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.collect_news_articles",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def collect_news_articles(self, sources, hours=24):
    """
    Collect news articles from specified sources for the given time period.
    
    Args:
        sources: List of news source identifiers (e.g., ['newsapi', 'finnhub', 'alphavantage'])
        hours: Number of hours to look back for news articles
        
    Returns:
        dict: Collection results with article count and source details
        
    Requirement: 23.4 - Process bulk data collection tasks asynchronously
    """
    logger.info("task_started", task="collect_news_articles", sources=sources, hours=hours)
    
    try:
        # TODO: Implement news collection from specific sources
        # This will be implemented in Phase 0.2.2
        results = {
            "articles_collected": 0,
            "sources_processed": sources,
            "hours": hours,
            "errors": []
        }
        
        for source in sources:
            try:
                # Collect from each source
                # Implementation will depend on NewsCollector class
                logger.info("collecting_from_source", source=source)
            except Exception as e:
                results["errors"].append({"source": source, "error": str(e)})
                logger.error("source_collection_failed", source=source, error=str(e))
        
        logger.info("task_completed", task="collect_news_articles", results=results)
        return results
        
    except Exception as exc:
        logger.error("task_failed", task="collect_news_articles", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.process_news",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def process_news(self, article_ids):
    """
    Process news articles: extract entities, calculate sentiment, categorize.
    
    Args:
        article_ids: List of article IDs to process
        
    Returns:
        dict: Processing results
        
    Requirement: 23.4 - Process bulk data collection tasks asynchronously
    """
    logger.info("task_started", task="process_news", article_count=len(article_ids))
    
    try:
        # TODO: Implement news processing
        # This will be implemented in Phase 0.2
        results = {
            "processed": 0,
            "failed": 0,
            "errors": []
        }
        
        logger.info("task_completed", task="process_news", results=results)
        return results
        
    except Exception as exc:
        logger.error("task_failed", task="process_news", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.process_news_sentiment",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def process_news_sentiment(self, article_ids):
    """
    Process sentiment analysis for specific news articles.
    
    Args:
        article_ids: List of article IDs to analyze for sentiment
        
    Returns:
        dict: Sentiment processing results with scores
        
    Requirement: 23.4 - Process bulk data collection tasks asynchronously
    """
    logger.info("task_started", task="process_news_sentiment", article_count=len(article_ids))
    
    try:
        # TODO: Implement sentiment processing for specific articles
        # This will be implemented in Phase 0.3.1
        results = {
            "processed": 0,
            "failed": 0,
            "average_sentiment": 0.0,
            "errors": []
        }
        
        for article_id in article_ids:
            try:
                # Process sentiment for each article
                # Implementation will use SentimentAnalyzer class
                logger.info("processing_sentiment", article_id=article_id)
                results["processed"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"article_id": article_id, "error": str(e)})
                logger.error("sentiment_processing_failed", article_id=article_id, error=str(e))
        
        logger.info("task_completed", task="process_news_sentiment", results=results)
        return results
        
    except Exception as exc:
        logger.error("task_failed", task="process_news_sentiment", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.analyze_news_sentiment",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def analyze_news_sentiment(self):
    """
    Analyze sentiment for recent unprocessed news articles.
    
    Returns:
        dict: Sentiment analysis results
        
    Requirement: 23.4 - Process bulk data collection tasks asynchronously
    """
    logger.info("task_started", task="analyze_news_sentiment")
    
    try:
        # TODO: Implement sentiment analysis
        # This will be implemented in Phase 0.2
        results = {
            "articles_analyzed": 0,
            "average_sentiment": 0.0,
            "errors": []
        }
        
        logger.info("task_completed", task="analyze_news_sentiment", results=results)
        return results
        
    except Exception as exc:
        logger.error("task_failed", task="analyze_news_sentiment", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.scan_top_movers",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def scan_top_movers(self):
    """
    Scan and identify top gaining and losing stocks.
    
    Returns:
        dict: Top movers data
        
    Requirement: 23.4 - Process bulk data collection tasks asynchronously
    """
    logger.info("task_started", task="scan_top_movers")
    
    try:
        # TODO: Implement top movers scanning
        # This will be implemented in Phase 0.2
        results = {
            "gainers": [],
            "losers": [],
            "unusual_volume": []
        }
        
        logger.info("task_completed", task="scan_top_movers", results=results)
        return results
        
    except Exception as exc:
        logger.error("task_failed", task="scan_top_movers", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.calculate_top_movers",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def calculate_top_movers(self, date):
    """
    Calculate top gaining and losing stocks for a specific date.
    
    Args:
        date: Date string in ISO format (YYYY-MM-DD) for which to calculate top movers
        
    Returns:
        dict: Top movers data with gainers and losers
        
    Requirement: 23.4 - Process bulk data collection tasks asynchronously
    """
    logger.info("task_started", task="calculate_top_movers", date=date)
    
    try:
        # TODO: Implement top movers calculation for specific date
        # This will be implemented in Phase 0.2.1
        results = {
            "date": date,
            "gainers": [],
            "losers": [],
            "unusual_volume": [],
            "count_gainers": 0,
            "count_losers": 0
        }
        
        # Implementation will use MoversProcessor class
        # to identify top 20 gainers and losers based on percentage change
        
        logger.info("task_completed", task="calculate_top_movers", results=results)
        return results
        
    except Exception as exc:
        logger.error("task_failed", task="calculate_top_movers", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.scan_penny_stocks",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def scan_penny_stocks(self):
    """
    Scan for penny stocks with sudden gains and momentum.
    
    Returns:
        dict: Penny stock movers data
        
    Requirement: 23.4 - Process bulk data collection tasks asynchronously
    """
    logger.info("task_started", task="scan_penny_stocks")
    
    try:
        # TODO: Implement penny stock scanning
        # This will be implemented in Phase 0.2
        results = {
            "penny_movers": [],
            "top_momentum": [],
            "count": 0
        }
        
        logger.info("task_completed", task="scan_penny_stocks", results=results)
        return results
        
    except Exception as exc:
        logger.error("task_failed", task="scan_penny_stocks", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.generate_daily_predictions",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def generate_daily_predictions(self, tickers=None):
    """
    Generate next-day price predictions for specified tickers or watchlist stocks.
    
    Args:
        tickers: List of ticker symbols or None for all watchlist stocks
        
    Returns:
        dict: Prediction generation results
        
    Requirement: 23.2 - Process ML model training tasks asynchronously
    """
    logger.info("task_started", task="generate_daily_predictions", tickers=tickers)
    
    try:
        # TODO: Implement daily predictions for specific tickers
        # This will be implemented in Phase 0.4.2
        
        if tickers is None:
            # Get tickers from watchlist
            tickers = []  # TODO: Load from watchlist
        
        results = {
            "predictions_generated": 0,
            "tickers": tickers,
            "failed": 0,
            "errors": []
        }
        
        for ticker in tickers:
            try:
                # Generate prediction for each ticker
                # Implementation will use EnsemblePredictor class
                logger.info("generating_prediction", ticker=ticker)
                results["predictions_generated"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"ticker": ticker, "error": str(e)})
                logger.error("prediction_generation_failed", ticker=ticker, error=str(e))
        
        logger.info("task_completed", task="generate_daily_predictions", results=results)
        return results
        
    except Exception as exc:
        logger.error("task_failed", task="generate_daily_predictions", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.train_ml_model",
    bind=True,
    max_retries=2,
    default_retry_delay=600,
    time_limit=7200,  # 2 hours for ML training
    soft_time_limit=6600,
)
def train_ml_model(self, ticker, model_type="ensemble"):
    """
    Train ML model for a specific ticker.
    
    Args:
        ticker: Stock ticker symbol
        model_type: Type of model to train (ensemble, lstm, transformer)
        
    Returns:
        dict: Training results with model performance metrics
        
    Requirement: 23.2 - Process ML model training tasks asynchronously
    """
    logger.info("task_started", task="train_ml_model", ticker=ticker, model_type=model_type)
    
    try:
        # Update task state to show progress
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Loading data..."}
        )
        
        # TODO: Implement ML model training
        # This will be implemented in Phase 1
        results = {
            "ticker": ticker,
            "model_type": model_type,
            "accuracy": 0.0,
            "training_time": 0.0,
            "model_path": ""
        }
        
        logger.info("task_completed", task="train_ml_model", results=results)
        return results
        
    except Exception as exc:
        logger.error("task_failed", task="train_ml_model", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.run_backtest",
    bind=True,
    max_retries=2,
    default_retry_delay=600,
    time_limit=7200,  # 2 hours for backtesting
    soft_time_limit=6600,
)
def run_backtest(self, strategy_id, start_date, end_date, initial_capital=100000):
    """
    Run backtest simulation for a trading strategy.
    
    Args:
        strategy_id: Strategy identifier
        start_date: Backtest start date (ISO format)
        end_date: Backtest end date (ISO format)
        initial_capital: Starting capital for backtest
        
    Returns:
        dict: Backtest results with performance metrics
        
    Requirement: 23.3 - Process backtest simulations asynchronously with progress tracking
    """
    logger.info(
        "task_started",
        task="run_backtest",
        strategy_id=strategy_id,
        start_date=start_date,
        end_date=end_date
    )
    
    try:
        # Update task state to show progress
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Initializing backtest..."}
        )
        
        # TODO: Implement backtesting
        # This will be implemented in Phase 2
        results = {
            "strategy_id": strategy_id,
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "trades": 0
        }
        
        logger.info("task_completed", task="run_backtest", results=results)
        return results
        
    except Exception as exc:
        logger.error("task_failed", task="run_backtest", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.calculate_technical_indicators",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def calculate_technical_indicators(self, ticker, indicators=None):
    """
    Calculate technical indicators for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        indicators: List of indicators to calculate or None for all
        
    Returns:
        dict: Calculated indicator values
        
    Requirement: 23.4 - Process bulk data collection tasks asynchronously
    """
    logger.info("task_started", task="calculate_technical_indicators", ticker=ticker)
    
    try:
        # TODO: Implement technical indicators calculation
        # This will be implemented in Phase 0.2
        results = {
            "ticker": ticker,
            "indicators": {},
            "timestamp": None
        }
        
        logger.info("task_completed", task="calculate_technical_indicators", results=results)
        return results
        
    except Exception as exc:
        logger.error("task_failed", task="calculate_technical_indicators", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.send_daily_reports",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def send_daily_reports(self):
    """
    Send daily market reports to all active users.
    
    Returns:
        dict: Report sending results
        
    Requirement: 23.1 - Asynchronous task processing
    """
    logger.info("task_started", task="send_daily_reports")
    
    try:
        # TODO: Implement daily report sending
        # This will be implemented in Phase 0.3
        results = {
            "reports_sent": 0,
            "failed": 0,
            "errors": []
        }
        
        logger.info("task_completed", task="send_daily_reports", results=results)
        return results
        
    except Exception as exc:
        logger.error("task_failed", task="send_daily_reports", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.send_daily_report",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def send_daily_report(self, user_id):
    """
    Send daily market report to a specific user.
    
    Args:
        user_id: User identifier to send the report to
        
    Returns:
        dict: Report sending result
        
    Requirement: 23.1 - Asynchronous task processing
    """
    logger.info("task_started", task="send_daily_report", user_id=user_id)
    
    try:
        # TODO: Implement daily report sending for specific user
        # This will be implemented in Phase 0.7.4
        
        result = {
            "user_id": user_id,
            "report_sent": True,
            "report_type": "daily_market_brief",
            "timestamp": None,
            "channels": []  # email, in-app, etc.
        }
        
        # Implementation will use DailyReportGenerator class
        # to generate and deliver report via configured channels
        
        logger.info("task_completed", task="send_daily_report", result=result)
        return result
        
    except Exception as exc:
        logger.error("task_failed", task="send_daily_report", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.send_alert",
    bind=True,
    max_retries=5,
    default_retry_delay=30,
)
def send_alert(self, user_id, alert_type, message, data=None):
    """
    Send alert to a specific user.
    
    Args:
        user_id: User identifier
        alert_type: Type of alert (price, news, sentiment, prediction)
        message: Alert message
        data: Additional alert data
        
    Returns:
        dict: Alert sending result
        
    Requirement: 23.1 - Asynchronous task processing
    """
    logger.info(
        "task_started",
        task="send_alert",
        user_id=user_id,
        alert_type=alert_type
    )
    
    try:
        # TODO: Implement alert sending
        # This will be implemented in Phase 0.3
        result = {
            "user_id": user_id,
            "alert_type": alert_type,
            "sent": True,
            "timestamp": None
        }
        
        logger.info("task_completed", task="send_alert", result=result)
        return result
        
    except Exception as exc:
        logger.error("task_failed", task="send_alert", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="stockiq.infrastructure.tasks.track_model_performance",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def track_model_performance(self):
    """
    Track and update ML model performance metrics.
    
    Returns:
        dict: Performance tracking results
        
    Requirement: 23.2 - Process ML model training tasks asynchronously
    """
    logger.info("task_started", task="track_model_performance")
    
    try:
        # TODO: Implement performance tracking
        # This will be implemented in Phase 1
        results = {
            "models_tracked": 0,
            "average_accuracy": 0.0,
            "models_needing_retraining": []
        }
        
        logger.info("task_completed", task="track_model_performance", results=results)
        return results
        
    except Exception as exc:
        logger.error("task_failed", task="track_model_performance", error=str(exc))
        raise self.retry(exc=exc)


# ============================================================================
# Utility Functions
# ============================================================================


def get_task_status(task_id):
    """
    Get status of a task by ID.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        dict: Task status information
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        "task_id": task_id,
        "state": result.state,
        "info": result.info,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "failed": result.failed() if result.ready() else None,
    }


def revoke_task(task_id, terminate=False):
    """
    Revoke (cancel) a task.
    
    Args:
        task_id: Celery task ID
        terminate: Whether to terminate the task if already executing
        
    Returns:
        bool: True if revoked successfully
    """
    try:
        celery_app.control.revoke(task_id, terminate=terminate)
        logger.info("task_revoked", task_id=task_id, terminate=terminate)
        return True
    except Exception as e:
        logger.error("task_revoke_failed", task_id=task_id, error=str(e))
        return False


def get_active_tasks():
    """
    Get list of currently active tasks.
    
    Returns:
        dict: Active tasks by worker
    """
    inspect = celery_app.control.inspect()
    return inspect.active()


def get_scheduled_tasks():
    """
    Get list of scheduled tasks.
    
    Returns:
        dict: Scheduled tasks by worker
    """
    inspect = celery_app.control.inspect()
    return inspect.scheduled()


def purge_queue(queue_name=None):
    """
    Purge all tasks from a queue.
    
    Args:
        queue_name: Name of queue to purge or None for all queues
        
    Returns:
        int: Number of tasks purged
    """
    if queue_name:
        return celery_app.control.purge(queue_name)
    else:
        return celery_app.control.purge()


# ============================================================================
# Health Check
# ============================================================================


@celery_app.task(name="stockiq.infrastructure.tasks.health_check")
def health_check():
    """
    Simple health check task to verify Celery is working.
    
    Returns:
        dict: Health check result
    """
    logger.info("health_check_task_executed")
    return {
        "status": "healthy",
        "message": "Celery task queue is operational",
        "timestamp": None
    }
