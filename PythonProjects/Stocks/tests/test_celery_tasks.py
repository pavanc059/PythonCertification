"""
Tests for Celery task definitions.

This test module verifies that all required task definitions exist
and have the correct signatures as per Phase 0.1.3 requirements.
"""

import pytest
from stockiq.infrastructure.tasks import (
    celery_app,
    collect_market_data,
    collect_news_articles,
    process_news_sentiment,
    calculate_top_movers,
    generate_daily_predictions,
    scan_penny_stocks,
    send_daily_report,
)


class TestCeleryTaskDefinitions:
    """Test that required Celery tasks are properly defined."""
    
    def test_collect_market_data_task_exists(self):
        """Test that collect_market_data task is registered."""
        task_name = "stockiq.infrastructure.tasks.collect_market_data"
        assert task_name in celery_app.tasks
        
    def test_collect_news_articles_task_exists(self):
        """Test that collect_news_articles task is registered."""
        task_name = "stockiq.infrastructure.tasks.collect_news_articles"
        assert task_name in celery_app.tasks
        
    def test_process_news_sentiment_task_exists(self):
        """Test that process_news_sentiment task is registered."""
        task_name = "stockiq.infrastructure.tasks.process_news_sentiment"
        assert task_name in celery_app.tasks
        
    def test_calculate_top_movers_task_exists(self):
        """Test that calculate_top_movers task is registered."""
        task_name = "stockiq.infrastructure.tasks.calculate_top_movers"
        assert task_name in celery_app.tasks
        
    def test_generate_daily_predictions_task_exists(self):
        """Test that generate_daily_predictions task is registered."""
        task_name = "stockiq.infrastructure.tasks.generate_daily_predictions"
        assert task_name in celery_app.tasks
        
    def test_scan_penny_stocks_task_exists(self):
        """Test that scan_penny_stocks task is registered."""
        task_name = "stockiq.infrastructure.tasks.scan_penny_stocks"
        assert task_name in celery_app.tasks
        
    def test_send_daily_report_task_exists(self):
        """Test that send_daily_report task is registered."""
        task_name = "stockiq.infrastructure.tasks.send_daily_report"
        assert task_name in celery_app.tasks


class TestCeleryTaskSignatures:
    """Test that task functions have the correct signatures."""
    
    def test_collect_market_data_signature(self):
        """Test collect_market_data has correct signature."""
        import inspect
        sig = inspect.signature(collect_market_data.run)
        params = list(sig.parameters.keys())
        assert 'tickers' in params
        
    def test_collect_news_articles_signature(self):
        """Test collect_news_articles has correct signature."""
        import inspect
        sig = inspect.signature(collect_news_articles.run)
        params = list(sig.parameters.keys())
        assert 'sources' in params
        assert 'hours' in params
        
    def test_process_news_sentiment_signature(self):
        """Test process_news_sentiment has correct signature."""
        import inspect
        sig = inspect.signature(process_news_sentiment.run)
        params = list(sig.parameters.keys())
        assert 'article_ids' in params
        
    def test_calculate_top_movers_signature(self):
        """Test calculate_top_movers has correct signature."""
        import inspect
        sig = inspect.signature(calculate_top_movers.run)
        params = list(sig.parameters.keys())
        assert 'date' in params
        
    def test_generate_daily_predictions_signature(self):
        """Test generate_daily_predictions has correct signature."""
        import inspect
        sig = inspect.signature(generate_daily_predictions.run)
        params = list(sig.parameters.keys())
        assert 'tickers' in params
        
    def test_send_daily_report_signature(self):
        """Test send_daily_report has correct signature."""
        import inspect
        sig = inspect.signature(send_daily_report.run)
        params = list(sig.parameters.keys())
        assert 'user_id' in params


class TestCeleryTaskRouting:
    """Test that tasks are routed to correct queues."""
    
    def test_data_tasks_routed_to_data_queue(self):
        """Test that data collection tasks are routed to data queue."""
        data_tasks = [
            "stockiq.infrastructure.tasks.collect_market_data",
            "stockiq.infrastructure.tasks.collect_news_articles",
            "stockiq.infrastructure.tasks.process_news_sentiment",
            "stockiq.infrastructure.tasks.calculate_top_movers",
            "stockiq.infrastructure.tasks.scan_penny_stocks",
        ]
        
        for task_name in data_tasks:
            route = celery_app.conf.task_routes.get(task_name)
            assert route is not None, f"Task {task_name} has no route"
            assert route["queue"] == "data", f"Task {task_name} not routed to data queue"
    
    def test_ml_tasks_routed_to_ml_queue(self):
        """Test that ML tasks are routed to ml queue."""
        ml_tasks = [
            "stockiq.infrastructure.tasks.generate_daily_predictions",
        ]
        
        for task_name in ml_tasks:
            route = celery_app.conf.task_routes.get(task_name)
            assert route is not None, f"Task {task_name} has no route"
            assert route["queue"] == "ml", f"Task {task_name} not routed to ml queue"
    
    def test_alert_tasks_routed_to_alerts_queue(self):
        """Test that alert tasks are routed to alerts queue."""
        alert_tasks = [
            "stockiq.infrastructure.tasks.send_daily_report",
        ]
        
        for task_name in alert_tasks:
            route = celery_app.conf.task_routes.get(task_name)
            assert route is not None, f"Task {task_name} has no route"
            assert route["queue"] == "alerts", f"Task {task_name} not routed to alerts queue"


class TestCeleryBeatSchedule:
    """Test that periodic tasks are scheduled correctly."""
    
    def test_news_collection_scheduled(self):
        """Test that news collection is scheduled every 30 minutes."""
        schedule_entry = celery_app.conf.beat_schedule.get("collect-news-every-30-minutes")
        assert schedule_entry is not None
        assert schedule_entry["task"] == "stockiq.infrastructure.tasks.collect_latest_news"
        
    def test_market_data_collection_scheduled(self):
        """Test that market data collection is scheduled every 5 minutes."""
        schedule_entry = celery_app.conf.beat_schedule.get("collect-market-data-every-5-minutes")
        assert schedule_entry is not None
        assert schedule_entry["task"] == "stockiq.infrastructure.tasks.collect_market_data"
        
    def test_daily_predictions_scheduled(self):
        """Test that daily predictions are scheduled at 7:00 AM."""
        schedule_entry = celery_app.conf.beat_schedule.get("generate-daily-predictions")
        assert schedule_entry is not None
        assert schedule_entry["task"] == "stockiq.infrastructure.tasks.generate_daily_predictions"
        
    def test_penny_stock_scan_scheduled(self):
        """Test that penny stock scanning is scheduled every 2 minutes."""
        schedule_entry = celery_app.conf.beat_schedule.get("scan-penny-stocks-every-2-minutes")
        assert schedule_entry is not None
        assert schedule_entry["task"] == "stockiq.infrastructure.tasks.scan_penny_stocks"


class TestCeleryConfiguration:
    """Test Celery configuration settings."""
    
    def test_celery_app_configured(self):
        """Test that Celery app is properly configured."""
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.accept_content == ["json"]
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True
        
    def test_task_queues_defined(self):
        """Test that required task queues are defined."""
        queue_names = [q.name for q in celery_app.conf.task_queues]
        assert "data" in queue_names
        assert "ml" in queue_names
        assert "alerts" in queue_names
        assert "celery" in queue_names  # Default queue
        
    def test_retry_configuration(self):
        """Test that retry configuration is set."""
        assert celery_app.conf.task_autoretry_for == (Exception,)
        assert celery_app.conf.task_retry_kwargs == {"max_retries": 3}
        assert celery_app.conf.task_retry_backoff is True
        assert celery_app.conf.task_retry_jitter is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
