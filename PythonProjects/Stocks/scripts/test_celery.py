"""
Script to test Celery configuration and connectivity.

This script verifies that Celery is properly configured and can connect
to Redis broker and result backend.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_celery_import():
    """Test if Celery app can be imported."""
    print("Testing Celery import...")
    try:
        from stockiq.infrastructure.tasks import celery_app
        print("✓ Successfully imported Celery app")
        return True
    except Exception as e:
        print(f"✗ Failed to import Celery app: {e}")
        return False


def test_celery_config():
    """Test Celery configuration."""
    print("\nTesting Celery configuration...")
    try:
        from stockiq.infrastructure.tasks import celery_app
        
        print(f"  Broker URL: {celery_app.conf.broker_url}")
        print(f"  Result Backend: {celery_app.conf.result_backend}")
        print(f"  Task Serializer: {celery_app.conf.task_serializer}")
        print(f"  Result Serializer: {celery_app.conf.result_serializer}")
        print(f"  Timezone: {celery_app.conf.timezone}")
        print(f"  Task Time Limit: {celery_app.conf.task_time_limit}s")
        print(f"  Worker Prefetch: {celery_app.conf.worker_prefetch_multiplier}")
        print("✓ Celery configuration loaded")
        return True
    except Exception as e:
        print(f"✗ Failed to load Celery configuration: {e}")
        return False


def test_registered_tasks():
    """Test registered tasks."""
    print("\nTesting registered tasks...")
    try:
        from stockiq.infrastructure.tasks import celery_app
        
        # Get registered tasks
        tasks = sorted([
            task for task in celery_app.tasks.keys()
            if task.startswith('stockiq')
        ])
        
        print(f"  Found {len(tasks)} registered tasks:")
        for task in tasks:
            print(f"    - {task}")
        
        print("✓ Tasks registered successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to get registered tasks: {e}")
        return False


def test_beat_schedule():
    """Test Beat schedule configuration."""
    print("\nTesting Beat schedule...")
    try:
        from stockiq.infrastructure.tasks import celery_app
        
        schedule = celery_app.conf.beat_schedule
        print(f"  Found {len(schedule)} scheduled tasks:")
        for name, config in schedule.items():
            print(f"    - {name}")
            print(f"      Task: {config['task']}")
            print(f"      Schedule: {config['schedule']}")
        
        print("✓ Beat schedule configured")
        return True
    except Exception as e:
        print(f"✗ Failed to load Beat schedule: {e}")
        return False


def test_queue_config():
    """Test queue configuration."""
    print("\nTesting queue configuration...")
    try:
        from stockiq.infrastructure.tasks import celery_app
        
        queues = celery_app.conf.task_queues
        print(f"  Found {len(queues)} configured queues:")
        for queue in queues:
            print(f"    - {queue.name} (routing_key: {queue.routing_key})")
        
        print("✓ Queues configured")
        return True
    except Exception as e:
        print(f"✗ Failed to load queue configuration: {e}")
        return False


def test_redis_connection():
    """Test Redis connection for broker and backend."""
    print("\nTesting Redis connection...")
    try:
        from stockiq.infrastructure.cache import get_redis_client
        
        client = get_redis_client()
        response = client.ping()
        
        if response:
            print("✓ Redis connection successful")
            
            # Test broker database
            broker_client = client
            broker_client.select(1)  # Broker is on DB 1
            broker_client.ping()
            print("✓ Broker Redis (DB 1) accessible")
            
            # Test result backend database
            broker_client.select(2)  # Result backend is on DB 2
            broker_client.ping()
            print("✓ Result backend Redis (DB 2) accessible")
            
            return True
        else:
            print("✗ Redis ping failed")
            return False
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        print("  Make sure Redis is running on localhost:6379")
        return False


def test_health_check_task():
    """Test health check task execution."""
    print("\nTesting health check task execution...")
    try:
        from stockiq.infrastructure.tasks import health_check
        
        # Run health check synchronously
        result = health_check()
        
        if result and result.get("status") == "healthy":
            print(f"✓ Health check passed: {result['message']}")
            return True
        else:
            print(f"✗ Health check failed: {result}")
            return False
    except Exception as e:
        print(f"✗ Health check task failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Celery Configuration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_celery_import),
        ("Configuration Test", test_celery_config),
        ("Registered Tasks Test", test_registered_tasks),
        ("Beat Schedule Test", test_beat_schedule),
        ("Queue Configuration Test", test_queue_config),
        ("Redis Connection Test", test_redis_connection),
        ("Health Check Task Test", test_health_check_task),
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
    
    if passed == total:
        print("\n🎉 All tests passed! Celery is properly configured.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
