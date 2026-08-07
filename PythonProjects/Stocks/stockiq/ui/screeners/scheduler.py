"""
Screener Scheduler

Schedules screener execution at specified times with result notifications.
"""

import json
import os
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, time, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time as time_module
from .storage import ScreenerStorage
from .executor import ScreenerExecutor


class ScheduleFrequency(Enum):
    """Frequency options for scheduled screeners"""
    ONCE = "once"
    DAILY = "daily"
    WEEKDAYS = "weekdays"
    WEEKLY = "weekly"
    CUSTOM = "custom"


@dataclass
class ScheduledScreener:
    """
    Represents a scheduled screener execution.
    
    Attributes:
        screener_name: Name of the saved screener to execute
        schedule_time: Time of day to execute (HH:MM format)
        frequency: How often to execute
        enabled: Whether the schedule is active
        last_run: Timestamp of last execution
        next_run: Timestamp of next scheduled execution
        notify_on_results: Whether to send notification when results found
        notify_channels: List of notification channels (email, webhook, etc.)
        result_limit: Optional limit on number of results to return
    """
    screener_name: str
    schedule_time: str  # HH:MM format
    frequency: ScheduleFrequency
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    notify_on_results: bool = True
    notify_channels: List[str] = None
    result_limit: Optional[int] = None
    schedule_id: Optional[str] = None
    
    def __post_init__(self):
        if self.notify_channels is None:
            self.notify_channels = ["in-app"]
        if self.schedule_id is None:
            self.schedule_id = f"{self.screener_name}_{datetime.now().timestamp()}"


class ScreenerScheduler:
    """
    Manages scheduled execution of screeners.
    
    Schedules are stored persistently and executed in background threads.
    """
    
    def __init__(
        self,
        storage: ScreenerStorage,
        executor: ScreenerExecutor,
        schedule_dir: Optional[str] = None
    ):
        """
        Initialize screener scheduler.
        
        Args:
            storage: ScreenerStorage instance for loading screeners
            executor: ScreenerExecutor instance for running screeners
            schedule_dir: Directory for storing schedule configuration
        """
        self.storage = storage
        self.executor = executor
        
        if schedule_dir is None:
            schedule_dir = os.path.join(
                os.path.expanduser("~"),
                ".stockiq",
                "schedules"
            )
        
        self.schedule_dir = Path(schedule_dir)
        self.schedule_dir.mkdir(parents=True, exist_ok=True)
        
        self.schedules: Dict[str, ScheduledScreener] = {}
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.notification_callbacks: List[Callable] = []
        
        # Load existing schedules
        self._load_schedules()
    
    def add_schedule(
        self,
        screener_name: str,
        schedule_time: str,
        frequency: ScheduleFrequency = ScheduleFrequency.DAILY,
        notify_on_results: bool = True,
        notify_channels: Optional[List[str]] = None,
        result_limit: Optional[int] = None
    ) -> str:
        """
        Add a new scheduled screener.
        
        Args:
            screener_name: Name of saved screener to schedule
            schedule_time: Time to execute (HH:MM format, 24-hour)
            frequency: Execution frequency
            notify_on_results: Whether to notify when results found
            notify_channels: Notification channels
            result_limit: Optional limit on results
        
        Returns:
            Schedule ID
        
        Raises:
            ValueError: If screener not found or invalid schedule time
        """
        # Validate screener exists
        if not self.storage.exists(screener_name):
            raise ValueError(f"Screener '{screener_name}' not found")
        
        # Validate time format
        try:
            datetime.strptime(schedule_time, "%H:%M")
        except ValueError:
            raise ValueError("schedule_time must be in HH:MM format (24-hour)")
        
        # Create schedule
        schedule = ScheduledScreener(
            screener_name=screener_name,
            schedule_time=schedule_time,
            frequency=frequency,
            notify_on_results=notify_on_results,
            notify_channels=notify_channels or ["in-app"],
            result_limit=result_limit
        )
        
        # Calculate next run time
        schedule.next_run = self._calculate_next_run(schedule)
        
        # Store schedule
        self.schedules[schedule.schedule_id] = schedule
        self._save_schedules()
        
        return schedule.schedule_id
    
    def remove_schedule(self, schedule_id: str) -> bool:
        """
        Remove a scheduled screener.
        
        Args:
            schedule_id: ID of schedule to remove
        
        Returns:
            True if removed, False if not found
        """
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            self._save_schedules()
            return True
        return False
    
    def enable_schedule(self, schedule_id: str) -> None:
        """Enable a disabled schedule"""
        if schedule_id in self.schedules:
            self.schedules[schedule_id].enabled = True
            self.schedules[schedule_id].next_run = self._calculate_next_run(
                self.schedules[schedule_id]
            )
            self._save_schedules()
    
    def disable_schedule(self, schedule_id: str) -> None:
        """Disable an active schedule"""
        if schedule_id in self.schedules:
            self.schedules[schedule_id].enabled = False
            self._save_schedules()
    
    def list_schedules(self) -> List[Dict[str, Any]]:
        """
        List all scheduled screeners.
        
        Returns:
            List of schedule dictionaries
        """
        return [asdict(schedule) for schedule in self.schedules.values()]
    
    def start(self) -> None:
        """Start the scheduler background thread"""
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop,
                daemon=True
            )
            self.scheduler_thread.start()
    
    def stop(self) -> None:
        """Stop the scheduler background thread"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
    
    def register_notification_callback(self, callback: Callable) -> None:
        """
        Register a callback for notifications.
        
        Callback signature: callback(schedule: ScheduledScreener, results: DataFrame)
        """
        self.notification_callbacks.append(callback)
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop (runs in background thread)"""
        while self.running:
            try:
                self._check_and_execute_schedules()
                time_module.sleep(60)  # Check every minute
            except Exception as e:
                print(f"Error in scheduler loop: {e}")
                time_module.sleep(60)
    
    def _check_and_execute_schedules(self) -> None:
        """Check for due schedules and execute them"""
        now = datetime.now()
        
        for schedule_id, schedule in list(self.schedules.items()):
            if not schedule.enabled:
                continue
            
            # Check if schedule is due
            if schedule.next_run:
                next_run_dt = datetime.fromisoformat(schedule.next_run)
                
                if now >= next_run_dt:
                    # Execute the screener
                    self._execute_scheduled_screener(schedule)
                    
                    # Update schedule
                    schedule.last_run = now.isoformat()
                    schedule.next_run = self._calculate_next_run(schedule)
                    self._save_schedules()
    
    def _execute_scheduled_screener(self, schedule: ScheduledScreener) -> None:
        """Execute a scheduled screener"""
        try:
            # Load screener
            screener = self.storage.load(schedule.screener_name)
            
            # Execute screener
            results = self.executor.execute(
                screener,
                limit=schedule.result_limit
            )
            
            # Send notifications if results found
            if schedule.notify_on_results and not results.empty:
                self._send_notifications(schedule, results)
            
        except Exception as e:
            print(f"Error executing scheduled screener '{schedule.screener_name}': {e}")
    
    def _send_notifications(self, schedule: ScheduledScreener, results) -> None:
        """Send notifications for screener results"""
        # Call registered callbacks
        for callback in self.notification_callbacks:
            try:
                callback(schedule, results)
            except Exception as e:
                print(f"Error in notification callback: {e}")
    
    def _calculate_next_run(self, schedule: ScheduledScreener) -> str:
        """Calculate next run time based on schedule"""
        now = datetime.now()
        schedule_time_obj = datetime.strptime(schedule.schedule_time, "%H:%M").time()
        
        # Combine today's date with schedule time
        next_run = datetime.combine(now.date(), schedule_time_obj)
        
        # If time has passed today, move to next occurrence
        if next_run <= now:
            if schedule.frequency == ScheduleFrequency.DAILY:
                next_run += timedelta(days=1)
            elif schedule.frequency == ScheduleFrequency.WEEKDAYS:
                next_run += timedelta(days=1)
                # Skip to next weekday
                while next_run.weekday() >= 5:  # Saturday=5, Sunday=6
                    next_run += timedelta(days=1)
            elif schedule.frequency == ScheduleFrequency.WEEKLY:
                next_run += timedelta(weeks=1)
            elif schedule.frequency == ScheduleFrequency.ONCE:
                # One-time schedule, disable after execution
                schedule.enabled = False
                return None
        
        return next_run.isoformat()
    
    def _save_schedules(self) -> None:
        """Save schedules to disk"""
        schedule_file = self.schedule_dir / "schedules.json"
        
        schedules_dict = {
            sid: asdict(schedule)
            for sid, schedule in self.schedules.items()
        }
        
        # Convert enum to string
        for schedule_dict in schedules_dict.values():
            schedule_dict['frequency'] = schedule_dict['frequency'].value
        
        with open(schedule_file, 'w', encoding='utf-8') as f:
            json.dump(schedules_dict, f, indent=2, ensure_ascii=False)
    
    def _load_schedules(self) -> None:
        """Load schedules from disk"""
        schedule_file = self.schedule_dir / "schedules.json"
        
        if not schedule_file.exists():
            return
        
        try:
            with open(schedule_file, 'r', encoding='utf-8') as f:
                schedules_dict = json.load(f)
            
            for sid, schedule_data in schedules_dict.items():
                # Convert string back to enum
                schedule_data['frequency'] = ScheduleFrequency(schedule_data['frequency'])
                
                schedule = ScheduledScreener(**schedule_data)
                self.schedules[sid] = schedule
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"⚠️  Warning: Could not load schedules: {e}")


def create_daily_premarket_schedule(
    scheduler: ScreenerScheduler,
    screener_name: str,
    premarket_time: str = "08:00"
) -> str:
    """
    Convenience function to create a daily pre-market screener schedule.
    
    Args:
        scheduler: ScreenerScheduler instance
        screener_name: Name of screener to schedule
        premarket_time: Time to run (default 8:00 AM)
    
    Returns:
        Schedule ID
    """
    return scheduler.add_schedule(
        screener_name=screener_name,
        schedule_time=premarket_time,
        frequency=ScheduleFrequency.WEEKDAYS,
        notify_on_results=True,
        notify_channels=["in-app", "email"]
    )
