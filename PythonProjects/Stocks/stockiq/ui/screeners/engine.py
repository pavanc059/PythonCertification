"""
Screener Engine

High-level API that integrates all screener components.
"""

from typing import List, Optional, Dict, Any, Callable
import pandas as pd
from .criteria import FilterCriteria, get_all_criteria, get_criteria_by_category, CriteriaType
from .builder import ScreenerBuilder, get_prebuilt_screener, list_prebuilt_screeners
from .executor import ScreenerExecutor, BatchScreenerExecutor
from .storage import ScreenerStorage
from .scheduler import ScreenerScheduler, ScheduleFrequency, create_daily_premarket_schedule
from .criteria import CompositeFilter


class ScreenerEngine:
    """
    High-level API for stock screening.
    
    Integrates builder, executor, storage, and scheduler components.
    
    Example:
        engine = ScreenerEngine(data_source=get_stock_data)
        
        # Build and execute a screener
        results = (engine.builder()
            .where("market_cap").greater_than(1_000_000_000)
            .and_where("pe_ratio").less_than(20)
            .execute())
        
        # Save screener
        engine.save_screener(screener, name="Value Stocks")
        
        # Schedule screener
        engine.schedule_screener("Value Stocks", "08:00", frequency="weekdays")
    """
    
    def __init__(
        self,
        data_source: Optional[Callable] = None,
        storage_dir: Optional[str] = None,
        schedule_dir: Optional[str] = None
    ):
        """
        Initialize screener engine.
        
        Args:
            data_source: Callable that returns stock data DataFrame
            storage_dir: Directory for storing saved screeners
            schedule_dir: Directory for storing schedules
        """
        self.executor = ScreenerExecutor(data_source=data_source)
        self.batch_executor = BatchScreenerExecutor(self.executor)
        self.storage = ScreenerStorage(storage_dir=storage_dir)
        self.scheduler = ScreenerScheduler(
            storage=self.storage,
            executor=self.executor,
            schedule_dir=schedule_dir
        )
    
    # Builder API
    
    def builder(self) -> ScreenerBuilder:
        """Get a new ScreenerBuilder instance"""
        return ScreenerBuilder()
    
    def get_prebuilt(self, name: str) -> Optional[CompositeFilter]:
        """Get a pre-built screener by name"""
        return get_prebuilt_screener(name)
    
    def list_prebuilt(self) -> List[str]:
        """List all pre-built screeners"""
        return list_prebuilt_screeners()
    
    # Criteria API
    
    def get_all_criteria(self) -> List[FilterCriteria]:
        """Get all available filter criteria"""
        return get_all_criteria()
    
    def get_criteria_by_category(self, category: CriteriaType) -> List[FilterCriteria]:
        """Get criteria by category"""
        return get_criteria_by_category(category)
    
    def get_criteria_categories(self) -> List[str]:
        """Get all criteria categories"""
        return [cat.value for cat in CriteriaType]
    
    # Execution API
    
    def execute(
        self,
        screener: CompositeFilter,
        stock_universe: Optional[pd.DataFrame] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Execute a screener.
        
        Args:
            screener: CompositeFilter to execute
            stock_universe: Optional stock data
            limit: Optional result limit
        
        Returns:
            DataFrame with matching stocks
        """
        return self.executor.execute(screener, stock_universe, limit)
    
    def execute_batch(
        self,
        screeners: List[CompositeFilter],
        stock_universe: Optional[pd.DataFrame] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Execute multiple screeners in parallel.
        
        Args:
            screeners: List of screeners to execute
            stock_universe: Optional stock data
        
        Returns:
            Dictionary mapping screener names to results
        """
        return self.batch_executor.execute_batch(screeners, stock_universe)
    
    def get_execution_stats(
        self,
        screener: CompositeFilter,
        stock_universe: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """Get execution statistics for a screener"""
        return self.executor.get_execution_stats(screener, stock_universe)
    
    # Storage API
    
    def save_screener(
        self,
        screener: CompositeFilter,
        name: Optional[str] = None,
        overwrite: bool = False
    ) -> str:
        """
        Save a screener.
        
        Args:
            screener: CompositeFilter to save
            name: Optional name (overrides screener.name)
            overwrite: Whether to overwrite existing
        
        Returns:
            Path to saved file
        """
        if name:
            screener.name = name
        return self.storage.save(screener, overwrite=overwrite)
    
    def load_screener(self, name: str) -> CompositeFilter:
        """Load a saved screener"""
        return self.storage.load(name)
    
    def delete_screener(self, name: str) -> bool:
        """Delete a saved screener"""
        return self.storage.delete(name)
    
    def list_saved_screeners(self) -> List[Dict[str, Any]]:
        """List all saved screeners"""
        return self.storage.list_screeners()
    
    def screener_exists(self, name: str) -> bool:
        """Check if a screener exists"""
        return self.storage.exists(name)
    
    # Scheduler API
    
    def schedule_screener(
        self,
        screener_name: str,
        schedule_time: str,
        frequency: str = "daily",
        notify_on_results: bool = True,
        notify_channels: Optional[List[str]] = None,
        result_limit: Optional[int] = None
    ) -> str:
        """
        Schedule a screener for automatic execution.
        
        Args:
            screener_name: Name of saved screener
            schedule_time: Time to execute (HH:MM)
            frequency: Execution frequency (daily, weekdays, weekly, once)
            notify_on_results: Whether to notify when results found
            notify_channels: Notification channels
            result_limit: Optional result limit
        
        Returns:
            Schedule ID
        """
        freq_enum = ScheduleFrequency(frequency)
        
        return self.scheduler.add_schedule(
            screener_name=screener_name,
            schedule_time=schedule_time,
            frequency=freq_enum,
            notify_on_results=notify_on_results,
            notify_channels=notify_channels,
            result_limit=result_limit
        )
    
    def unschedule_screener(self, schedule_id: str) -> bool:
        """Remove a scheduled screener"""
        return self.scheduler.remove_schedule(schedule_id)
    
    def enable_schedule(self, schedule_id: str) -> None:
        """Enable a disabled schedule"""
        self.scheduler.enable_schedule(schedule_id)
    
    def disable_schedule(self, schedule_id: str) -> None:
        """Disable an active schedule"""
        self.scheduler.disable_schedule(schedule_id)
    
    def list_schedules(self) -> List[Dict[str, Any]]:
        """List all scheduled screeners"""
        return self.scheduler.list_schedules()
    
    def start_scheduler(self) -> None:
        """Start the scheduler background thread"""
        self.scheduler.start()
    
    def stop_scheduler(self) -> None:
        """Stop the scheduler background thread"""
        self.scheduler.stop()
    
    def register_notification_callback(self, callback: Callable) -> None:
        """Register a notification callback"""
        self.scheduler.register_notification_callback(callback)
    
    # Convenience methods
    
    def quick_screen(
        self,
        prebuilt_name: str,
        stock_universe: Optional[pd.DataFrame] = None,
        limit: int = 50
    ) -> pd.DataFrame:
        """
        Quickly execute a pre-built screener.
        
        Args:
            prebuilt_name: Name of pre-built screener
            stock_universe: Optional stock data
            limit: Result limit
        
        Returns:
            DataFrame with matching stocks
        """
        screener = self.get_prebuilt(prebuilt_name)
        if screener is None:
            raise ValueError(f"Pre-built screener '{prebuilt_name}' not found")
        
        return self.execute(screener, stock_universe, limit)
    
    def create_and_save(
        self,
        name: str,
        description: str,
        builder_func: Callable[[ScreenerBuilder], ScreenerBuilder]
    ) -> str:
        """
        Create and save a screener using a builder function.
        
        Example:
            engine.create_and_save(
                name="My Screener",
                description="Custom screener",
                builder_func=lambda b: b
                    .where("market_cap").greater_than(1e9)
                    .and_where("pe_ratio").less_than(20)
            )
        
        Args:
            name: Screener name
            description: Screener description
            builder_func: Function that builds the screener
        
        Returns:
            Path to saved file
        """
        builder = self.builder().with_name(name).with_description(description)
        builder = builder_func(builder)
        screener = builder.build()
        return self.save_screener(screener)
    
    def schedule_premarket(
        self,
        screener_name: str,
        time: str = "08:00"
    ) -> str:
        """
        Schedule a screener for daily pre-market execution.
        
        Args:
            screener_name: Name of saved screener
            time: Pre-market time (default 8:00 AM)
        
        Returns:
            Schedule ID
        """
        return create_daily_premarket_schedule(
            self.scheduler,
            screener_name,
            time
        )
    
    # Cache management
    
    def clear_cache(self) -> None:
        """Clear the execution cache"""
        self.executor.clear_cache()
    
    def set_cache_ttl(self, seconds: int) -> None:
        """Set cache time-to-live"""
        self.executor.set_cache_ttl(seconds)
