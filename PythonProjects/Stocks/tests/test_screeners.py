"""
Tests for Stock Screener System

Tests cover:
- Filter criteria definitions and validation
- Screener builder fluent API
- Screener executor with performance requirements
- Screener storage and persistence
- Screener scheduler with various frequencies
- End-to-end screener workflows
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import shutil
import time
from pathlib import Path

from stockiq.ui.screeners import (
    ScreenerEngine,
    FilterCriteria,
    FilterOperator,
    CriteriaType,
    ScreenerBuilder,
    ScreenerExecutor,
    ScreenerStorage,
    ScreenerScheduler,
)
from stockiq.ui.screeners.criteria import (
    ComparisonOperator,
    FilterCondition,
    CompositeFilter,
    AVAILABLE_CRITERIA,
    get_criteria_by_name,
)
from stockiq.ui.screeners.scheduler import ScheduleFrequency


# Test Fixtures

@pytest.fixture
def sample_stock_data():
    """Generate sample stock data for testing"""
    np.random.seed(42)
    n_stocks = 1000
    
    sectors = ["Technology", "Healthcare", "Finance", "Energy", "Consumer"]
    exchanges = ["NYSE", "NASDAQ", "AMEX"]
    
    data = pd.DataFrame({
        'ticker': [f'STOCK{i:04d}' for i in range(n_stocks)],
        'price': np.random.uniform(1, 500, n_stocks),
        'market_cap': np.random.uniform(100_000_000, 100_000_000_000, n_stocks),
        'volume': np.random.randint(10_000, 50_000_000, n_stocks),
        'avg_volume': np.random.randint(50_000, 10_000_000, n_stocks),
        'pe_ratio': np.random.uniform(5, 50, n_stocks),
        'pb_ratio': np.random.uniform(0.5, 10, n_stocks),
        'dividend_yield': np.random.uniform(0, 8, n_stocks),
        'debt_to_equity': np.random.uniform(0, 3, n_stocks),
        'revenue_growth': np.random.uniform(-20, 100, n_stocks),
        'earnings_growth': np.random.uniform(-30, 150, n_stocks),
        'rsi': np.random.uniform(20, 80, n_stocks),
        'sentiment_score': np.random.uniform(-1, 1, n_stocks),
        'return_1w': np.random.uniform(-15, 30, n_stocks),
        'return_1m': np.random.uniform(-25, 50, n_stocks),
        'return_ytd': np.random.uniform(-40, 100, n_stocks),
        'beta': np.random.uniform(0.3, 2.5, n_stocks),
        'volatility': np.random.uniform(10, 80, n_stocks),
        'sector': np.random.choice(sectors, n_stocks),
        'exchange': np.random.choice(exchanges, n_stocks),
    })
    
    # Add calculated fields
    data['price_change_pct'] = np.random.uniform(-10, 15, n_stocks)
    data['volume_ratio'] = data['volume'] / data['avg_volume']
    
    return data


@pytest.fixture
def temp_storage_dir():
    """Create temporary directory for screener storage"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def screener_storage(temp_storage_dir):
    """Create ScreenerStorage instance"""
    return ScreenerStorage(storage_dir=temp_storage_dir)


@pytest.fixture
def screener_executor(sample_stock_data):
    """Create ScreenerExecutor instance"""
    return ScreenerExecutor(data_source=lambda: sample_stock_data)


@pytest.fixture
def screener_engine(sample_stock_data, temp_storage_dir):
    """Create ScreenerEngine instance"""
    return ScreenerEngine(
        data_source=lambda: sample_stock_data,
        storage_dir=temp_storage_dir,
        schedule_dir=temp_storage_dir
    )


# Test Filter Criteria

class TestFilterCriteria:
    """Test filter criteria definitions"""
    
    def test_criteria_count(self):
        """Test that we have at least 20 filter criteria (Requirement 17.7)"""
        assert len(AVAILABLE_CRITERIA) >= 20
    
    def test_criteria_categories(self):
        """Test criteria are properly categorized"""
        categories = set(c.category for c in AVAILABLE_CRITERIA.values())
        assert len(categories) > 0
        assert CriteriaType.PRICE in categories
        assert CriteriaType.TECHNICAL in categories
        assert CriteriaType.FUNDAMENTAL in categories
    
    def test_criteria_validation(self):
        """Test value validation for criteria"""
        price_criteria = get_criteria_by_name("price")
        
        assert price_criteria.validate_value(100.5)
        assert price_criteria.validate_value(0)
        assert not price_criteria.validate_value("invalid")
    
    def test_all_criteria_have_operators(self):
        """Test all criteria have valid operators defined"""
        for criteria in AVAILABLE_CRITERIA.values():
            assert len(criteria.valid_operators) > 0
            assert criteria.default_operator in criteria.valid_operators


# Test Screener Builder

class TestScreenerBuilder:
    """Test screener builder fluent API"""
    
    def test_simple_screener(self):
        """Test building a simple screener"""
        screener = (ScreenerBuilder()
            .with_name("Test Screener")
            .where("price").greater_than(50)
            .build())
        
        assert screener.name == "Test Screener"
        assert len(screener.conditions) == 1
        assert screener.conditions[0].criteria.name == "price"
    
    def test_and_conditions(self):
        """Test AND logic (Requirement 17.8)"""
        screener = (ScreenerBuilder()
            .where("price").greater_than(50)
            .and_where("market_cap").greater_than(1_000_000_000)
            .and_where("pe_ratio").less_than(20)
            .build())
        
        assert len(screener.conditions) == 3
        assert screener.operator == FilterOperator.AND
    
    def test_or_conditions(self):
        """Test OR logic (Requirement 17.8)"""
        screener = (ScreenerBuilder()
            .where("sector").equals("Technology")
            .or_where("sector").equals("Healthcare")
            .build())
        
        assert len(screener.conditions) == 2
        assert screener.operator == FilterOperator.OR
    
    def test_between_operator(self):
        """Test BETWEEN operator"""
        screener = (ScreenerBuilder()
            .where("pe_ratio").between(10, 25)
            .build())
        
        condition = screener.conditions[0]
        assert condition.operator == ComparisonOperator.BETWEEN
        assert condition.value == [10, 25]
    
    def test_in_operator(self):
        """Test IN operator"""
        screener = (ScreenerBuilder()
            .where("sector").in_list(["Technology", "Healthcare", "Finance"])
            .build())
        
        condition = screener.conditions[0]
        assert condition.operator == ComparisonOperator.IN
        assert len(condition.value) == 3
    
    def test_invalid_operator_raises_error(self):
        """Test that invalid operators raise errors"""
        with pytest.raises(ValueError):
            (ScreenerBuilder()
                .where("price").in_list([10, 20, 30])  # IN not valid for price
                .build())
    
    def test_prebuilt_screeners(self):
        """Test pre-built screeners"""
        from stockiq.ui.screeners.builder import (
            create_value_screener,
            create_growth_screener,
            create_momentum_screener
        )
        
        value = create_value_screener()
        assert value.name == "Value Stocks"
        assert len(value.conditions) >= 3
        
        growth = create_growth_screener()
        assert growth.name == "Growth Stocks"
        
        momentum = create_momentum_screener()
        assert momentum.name == "Momentum Stocks"


# Test Screener Executor

class TestScreenerExecutor:
    """Test screener execution and performance"""
    
    def test_simple_execution(self, screener_executor, sample_stock_data):
        """Test basic screener execution"""
        screener = (ScreenerBuilder()
            .where("price").greater_than(100)
            .build())
        
        results = screener_executor.execute(screener, sample_stock_data)
        
        assert not results.empty
        assert all(results['price'] > 100)
    
    def test_and_logic_execution(self, screener_executor, sample_stock_data):
        """Test AND logic execution"""
        screener = (ScreenerBuilder()
            .where("price").greater_than(100)
            .and_where("market_cap").greater_than(1_000_000_000)
            .and_where("pe_ratio").less_than(20)
            .build())
        
        results = screener_executor.execute(screener, sample_stock_data)
        
        if not results.empty:
            assert all(results['price'] > 100)
            assert all(results['market_cap'] > 1_000_000_000)
            assert all(results['pe_ratio'] < 20)
    
    def test_or_logic_execution(self, screener_executor, sample_stock_data):
        """Test OR logic execution"""
        screener = (ScreenerBuilder()
            .with_operator(FilterOperator.OR)
            .where("sector").equals("Technology")
            .or_where("sector").equals("Healthcare")
            .build())
        
        results = screener_executor.execute(screener, sample_stock_data)
        
        assert not results.empty
        assert all(results['sector'].isin(["Technology", "Healthcare"]))
    
    def test_between_execution(self, screener_executor, sample_stock_data):
        """Test BETWEEN operator execution"""
        screener = (ScreenerBuilder()
            .where("pe_ratio").between(10, 20)
            .build())
        
        results = screener_executor.execute(screener, sample_stock_data)
        
        if not results.empty:
            assert all((results['pe_ratio'] >= 10) & (results['pe_ratio'] <= 20))
    
    def test_performance_requirement(self, screener_executor, sample_stock_data):
        """Test sub-5-second execution across 1,000 stocks (Requirement 17.9)"""
        screener = (ScreenerBuilder()
            .where("price").greater_than(50)
            .and_where("market_cap").greater_than(500_000_000)
            .and_where("pe_ratio").less_than(30)
            .and_where("volume_ratio").greater_than(1.0)
            .build())
        
        start_time = time.time()
        results = screener_executor.execute(screener, sample_stock_data)
        execution_time = time.time() - start_time
        
        # Should execute in under 5 seconds (Requirement 17.9)
        assert execution_time < 5.0, f"Execution took {execution_time:.2f}s (target: <5s)"
    
    def test_large_dataset_performance(self, screener_executor):
        """Test performance with 5,000+ stocks"""
        # Generate larger dataset
        np.random.seed(42)
        n_stocks = 5000
        
        large_data = pd.DataFrame({
            'ticker': [f'STOCK{i:04d}' for i in range(n_stocks)],
            'price': np.random.uniform(1, 500, n_stocks),
            'market_cap': np.random.uniform(100_000_000, 100_000_000_000, n_stocks),
            'pe_ratio': np.random.uniform(5, 50, n_stocks),
            'volume_ratio': np.random.uniform(0.5, 5, n_stocks),
        })
        
        screener = (ScreenerBuilder()
            .where("price").greater_than(50)
            .and_where("market_cap").greater_than(1_000_000_000)
            .and_where("pe_ratio").less_than(25)
            .build())
        
        start_time = time.time()
        results = screener_executor.execute(screener, large_data)
        execution_time = time.time() - start_time
        
        # Should still be under 5 seconds with 5,000 stocks
        assert execution_time < 5.0, f"Execution took {execution_time:.2f}s with {n_stocks} stocks"
    
    def test_result_limit(self, screener_executor, sample_stock_data):
        """Test result limiting"""
        screener = (ScreenerBuilder()
            .where("price").greater_than(1)
            .build())
        
        results = screener_executor.execute(screener, sample_stock_data, limit=10)
        
        assert len(results) <= 10
    
    def test_execution_stats(self, screener_executor, sample_stock_data):
        """Test execution statistics"""
        screener = (ScreenerBuilder()
            .where("price").greater_than(100)
            .build())
        
        stats = screener_executor.get_execution_stats(screener, sample_stock_data)
        
        assert 'execution_time_seconds' in stats
        assert 'result_count' in stats
        assert 'total_stocks_scanned' in stats
        assert 'meets_performance_target' in stats
        assert stats['meets_performance_target'] is True


# Test Screener Storage

class TestScreenerStorage:
    """Test screener persistence (Requirement 17.10)"""
    
    def test_save_and_load(self, screener_storage):
        """Test saving and loading screeners"""
        screener = (ScreenerBuilder()
            .with_name("Test Screener")
            .with_description("A test screener")
            .where("price").greater_than(50)
            .and_where("market_cap").greater_than(1_000_000_000)
            .build())
        
        # Save
        filepath = screener_storage.save(screener)
        assert Path(filepath).exists()
        
        # Load
        loaded = screener_storage.load("Test Screener")
        assert loaded.name == "Test Screener"
        assert loaded.description == "A test screener"
        assert len(loaded.conditions) == 2
    
    def test_save_without_name_raises_error(self, screener_storage):
        """Test that saving without name raises error"""
        screener = (ScreenerBuilder()
            .where("price").greater_than(50)
            .build())
        
        with pytest.raises(ValueError):
            screener_storage.save(screener)
    
    def test_overwrite_protection(self, screener_storage):
        """Test overwrite protection"""
        screener = (ScreenerBuilder()
            .with_name("Test Screener")
            .where("price").greater_than(50)
            .build())
        
        # Save first time
        screener_storage.save(screener)
        
        # Try to save again without overwrite flag
        with pytest.raises(ValueError):
            screener_storage.save(screener)
        
        # Should work with overwrite flag
        screener_storage.save(screener, overwrite=True)
    
    def test_list_screeners(self, screener_storage):
        """Test listing saved screeners"""
        # Save multiple screeners
        for i in range(3):
            screener = (ScreenerBuilder()
                .with_name(f"Screener {i}")
                .where("price").greater_than(50)
                .build())
            screener_storage.save(screener)
        
        screeners = screener_storage.list_screeners()
        assert len(screeners) == 3
        assert all('name' in s for s in screeners)
        assert all('condition_count' in s for s in screeners)
    
    def test_delete_screener(self, screener_storage):
        """Test deleting screeners"""
        screener = (ScreenerBuilder()
            .with_name("To Delete")
            .where("price").greater_than(50)
            .build())
        
        screener_storage.save(screener)
        assert screener_storage.exists("To Delete")
        
        deleted = screener_storage.delete("To Delete")
        assert deleted is True
        assert not screener_storage.exists("To Delete")
    
    def test_export_import(self, screener_storage, temp_storage_dir):
        """Test export and import"""
        screener = (ScreenerBuilder()
            .with_name("Export Test")
            .where("price").greater_than(50)
            .build())
        
        screener_storage.save(screener)
        
        # Export
        export_path = Path(temp_storage_dir) / "exported.json"
        screener_storage.export_screener("Export Test", str(export_path))
        assert export_path.exists()
        
        # Delete original
        screener_storage.delete("Export Test")
        
        # Import with new name
        screener_storage.import_screener(str(export_path), new_name="Imported")
        assert screener_storage.exists("Imported")


# Test Screener Scheduler

class TestScreenerScheduler:
    """Test screener scheduling (Requirement 17.11)"""
    
    def test_add_schedule(self, screener_engine):
        """Test adding a schedule"""
        # Create and save a screener first
        screener = (ScreenerBuilder()
            .with_name("Daily Screener")
            .where("price").greater_than(50)
            .build())
        screener_engine.save_screener(screener)
        
        # Schedule it
        schedule_id = screener_engine.schedule_screener(
            screener_name="Daily Screener",
            schedule_time="09:00",
            frequency="daily"
        )
        
        assert schedule_id is not None
        
        schedules = screener_engine.list_schedules()
        assert len(schedules) == 1
        assert schedules[0]['screener_name'] == "Daily Screener"
        assert schedules[0]['schedule_time'] == "09:00"
    
    def test_schedule_frequencies(self, screener_engine):
        """Test different schedule frequencies"""
        screener = (ScreenerBuilder()
            .with_name("Test Screener")
            .where("price").greater_than(50)
            .build())
        screener_engine.save_screener(screener)
        
        frequencies = ["daily", "weekdays", "weekly", "once"]
        
        for freq in frequencies:
            schedule_id = screener_engine.schedule_screener(
                screener_name="Test Screener",
                schedule_time="10:00",
                frequency=freq
            )
            assert schedule_id is not None
            screener_engine.unschedule_screener(schedule_id)
    
    def test_enable_disable_schedule(self, screener_engine):
        """Test enabling and disabling schedules"""
        screener = (ScreenerBuilder()
            .with_name("Toggle Screener")
            .where("price").greater_than(50)
            .build())
        screener_engine.save_screener(screener)
        
        schedule_id = screener_engine.schedule_screener(
            screener_name="Toggle Screener",
            schedule_time="11:00"
        )
        
        # Disable
        screener_engine.disable_schedule(schedule_id)
        schedules = screener_engine.list_schedules()
        assert schedules[0]['enabled'] is False
        
        # Enable
        screener_engine.enable_schedule(schedule_id)
        schedules = screener_engine.list_schedules()
        assert schedules[0]['enabled'] is True
    
    def test_remove_schedule(self, screener_engine):
        """Test removing a schedule"""
        screener = (ScreenerBuilder()
            .with_name("Remove Screener")
            .where("price").greater_than(50)
            .build())
        screener_engine.save_screener(screener)
        
        schedule_id = screener_engine.schedule_screener(
            screener_name="Remove Screener",
            schedule_time="12:00"
        )
        
        removed = screener_engine.unschedule_screener(schedule_id)
        assert removed is True
        
        schedules = screener_engine.list_schedules()
        assert len(schedules) == 0
    
    def test_invalid_time_format_raises_error(self, screener_engine):
        """Test invalid time format raises error"""
        screener = (ScreenerBuilder()
            .with_name("Invalid Time")
            .where("price").greater_than(50)
            .build())
        screener_engine.save_screener(screener)
        
        with pytest.raises(ValueError):
            screener_engine.schedule_screener(
                screener_name="Invalid Time",
                schedule_time="25:00"  # Invalid hour
            )
    
    def test_schedule_nonexistent_screener_raises_error(self, screener_engine):
        """Test scheduling nonexistent screener raises error"""
        with pytest.raises(ValueError):
            screener_engine.schedule_screener(
                screener_name="Nonexistent",
                schedule_time="10:00"
            )


# Test Screener Engine

class TestScreenerEngine:
    """Test high-level screener engine API"""
    
    def test_builder_api(self, screener_engine):
        """Test builder API"""
        builder = screener_engine.builder()
        assert isinstance(builder, ScreenerBuilder)
    
    def test_prebuilt_screeners(self, screener_engine):
        """Test pre-built screeners"""
        prebuilt_names = screener_engine.list_prebuilt()
        assert len(prebuilt_names) > 0
        
        for name in prebuilt_names:
            screener = screener_engine.get_prebuilt(name)
            assert screener is not None
            assert screener.name is not None
    
    def test_quick_screen(self, screener_engine):
        """Test quick screening with pre-built screeners"""
        results = screener_engine.quick_screen("value", limit=20)
        assert len(results) <= 20
    
    def test_criteria_api(self, screener_engine):
        """Test criteria retrieval API"""
        all_criteria = screener_engine.get_all_criteria()
        assert len(all_criteria) >= 20
        
        categories = screener_engine.get_criteria_categories()
        assert len(categories) > 0
        
        price_criteria = screener_engine.get_criteria_by_category(CriteriaType.PRICE)
        assert len(price_criteria) > 0
    
    def test_end_to_end_workflow(self, screener_engine):
        """Test complete end-to-end workflow"""
        # Build screener
        screener = (screener_engine.builder()
            .with_name("E2E Test")
            .with_description("End-to-end test screener")
            .where("price").greater_than(100)
            .and_where("market_cap").greater_than(1_000_000_000)
            .and_where("pe_ratio").less_than(25)
            .build())
        
        # Execute
        results = screener_engine.execute(screener, limit=50)
        assert len(results) <= 50
        
        # Save
        screener_engine.save_screener(screener)
        assert screener_engine.screener_exists("E2E Test")
        
        # Load and re-execute
        loaded = screener_engine.load_screener("E2E Test")
        results2 = screener_engine.execute(loaded, limit=50)
        assert len(results2) == len(results)
        
        # Schedule
        schedule_id = screener_engine.schedule_screener(
            screener_name="E2E Test",
            schedule_time="08:00",
            frequency="weekdays"
        )
        assert schedule_id is not None
        
        # Clean up
        screener_engine.unschedule_screener(schedule_id)
        screener_engine.delete_screener("E2E Test")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
