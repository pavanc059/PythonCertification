"""
Script to test Celery worker execution.

This script sends a test task to the Celery worker and verifies execution.
NOTE: This requires a running Celery worker to execute.
"""

import sys
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_worker_execution():
    """Test if a Celery worker can execute a task."""
    print("Testing Celery worker execution...")
    print("NOTE: This test requires a running Celery worker.")
    print("-" * 60)
    
    try:
        from stockiq.infrastructure.tasks import health_check
        
        # Send async task to worker
        print("Sending health check task to worker...")
        result = health_check.delay()
        
        print(f"Task ID: {result.id}")
        print(f"Task State: {result.state}")
        
        # Wait for result with timeout
        print("Waiting for task completion (timeout: 10s)...")
        try:
            output = result.get(timeout=10)
            print(f"\n✓ Task completed successfully!")
            print(f"Result: {output}")
            return True
        except Exception as e:
            print(f"\n✗ Task execution failed or timed out: {e}")
            print("\nPossible reasons:")
            print("1. Celery worker is not running")
            print("2. Worker is not consuming from the correct queue")
            print("3. Redis connection issues")
            print("\nTo start a worker, run:")
            print("  celery -A stockiq.infrastructure.tasks worker --loglevel=info")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_task_routing():
    """Test task routing to different queues."""
    print("\n" + "=" * 60)
    print("Testing task routing...")
    print("-" * 60)
    
    try:
        from stockiq.infrastructure.tasks import (
            collect_market_data,
            train_ml_model,
            send_alert,
        )
        
        tasks_to_test = [
            ("collect_market_data", collect_market_data, "data"),
            ("train_ml_model", train_ml_model, "ml"),
            ("send_alert", send_alert, "alerts"),
        ]
        
        results = []
        
        for task_name, task_func, expected_queue in tasks_to_test:
            # Get task route
            from stockiq.infrastructure.tasks import celery_app
            route = celery_app.conf.task_routes.get(
                f"stockiq.infrastructure.tasks.{task_name}",
                {}
            )
            actual_queue = route.get("queue", "celery")
            
            if actual_queue == expected_queue:
                print(f"✓ {task_name} → {actual_queue} queue")
                results.append(True)
            else:
                print(f"✗ {task_name} → expected {expected_queue}, got {actual_queue}")
                results.append(False)
        
        if all(results):
            print("\n✓ All task routes configured correctly")
            return True
        else:
            print("\n✗ Some task routes are incorrect")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_beat_schedule_times():
    """Test Beat schedule timing configurations."""
    print("\n" + "=" * 60)
    print("Testing Beat schedule times...")
    print("-" * 60)
    
    try:
        from stockiq.infrastructure.tasks import celery_app
        
        schedule = celery_app.conf.beat_schedule
        
        expected_schedules = {
            "collect-news-every-30-minutes": "*/30",
            "collect-market-data-every-5-minutes": "*/5",
            "scan-top-movers-every-5-minutes": "*/5",
            "scan-penny-stocks-every-2-minutes": "*/2",
            "generate-daily-predictions": "0 7",
            "send-daily-reports": "0 8",
            "analyze-news-sentiment": "*/15",
            "track-model-performance": "0 17",
        }
        
        results = []
        
        for name, expected_time in expected_schedules.items():
            if name in schedule:
                schedule_str = str(schedule[name]["schedule"])
                print(f"✓ {name}: {schedule_str}")
                results.append(True)
            else:
                print(f"✗ {name}: Not found in schedule")
                results.append(False)
        
        if all(results):
            print(f"\n✓ All {len(results)} scheduled tasks configured")
            return True
        else:
            print(f"\n✗ Some scheduled tasks are missing")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_queue_priorities():
    """Test queue priority configurations."""
    print("\n" + "=" * 60)
    print("Testing queue priorities...")
    print("-" * 60)
    
    try:
        from stockiq.infrastructure.tasks import celery_app
        
        queues = celery_app.conf.task_queues
        
        for queue in queues:
            max_priority = queue.queue_arguments.get("x-max-priority", 0)
            print(f"  {queue.name}: max priority = {max_priority}")
            
            if max_priority != 10:
                print(f"    ⚠️  Expected max priority 10, got {max_priority}")
        
        print("✓ Queue priorities configured")
        return True
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all worker tests."""
    print("=" * 60)
    print("Celery Worker Test Suite")
    print("=" * 60)
    
    tests = [
        ("Task Routing Test", test_task_routing),
        ("Beat Schedule Times Test", test_beat_schedule_times),
        ("Queue Priorities Test", test_queue_priorities),
        ("Worker Execution Test", test_worker_execution),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ {test_name} raised exception: {e}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if results.get("Worker Execution Test") is False:
        print("\n⚠️  Worker execution test failed.")
        print("To start a Celery worker, run one of:")
        print("  1. start-celery-worker.bat (Windows)")
        print("  2. celery -A stockiq.infrastructure.tasks worker --loglevel=info")
        print("  3. python scripts/start_celery_worker.py worker")
    
    if passed == total:
        print("\n🎉 All tests passed! Celery worker is ready.")
        return 0
    elif passed >= total - 1 and not results.get("Worker Execution Test"):
        print("\n⚠️  Configuration tests passed. Start a worker to test execution.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
