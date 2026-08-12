# Celery Task Queue Setup

## Overview

This document describes the Celery task queue configuration for the StockIQ platform. Celery provides asynchronous task processing for heavy computations, data collection, and scheduled tasks.

## Requirements

- **Requirement 23.1**: Asynchronous task processing using Celery
- **Requirement 23.2**: Process ML model training tasks asynchronously
- **Requirement 23.3**: Process backtest simulations asynchronously with progress tracking
- **Requirement 23.4**: Process bulk data collection tasks asynchronously

## Architecture

### Components

1. **Celery Application** (`stockiq/infrastructure/tasks.py`)
   - Central Celery application instance
   - Task definitions
   - Queue configuration
   - Beat schedule

2. **Redis Backend**
   - Message broker: `redis://localhost:6379/1`
   - Result backend: `redis://localhost:6379/2`
   - Pub/sub for real-time updates

3. **Worker Pools**
   - Default configuration: 4-8 workers
   - Autoscaling: 2x concurrency maximum
   - Pool type: prefork (process-based)

4. **Task Queues**
   - `data`: Data collection and processing tasks
   - `ml`: Machine learning and prediction tasks
   - `alerts`: Alert and notification tasks
   - `celery`: Default queue for general tasks

### Task Routing

Tasks are automatically routed based on their names:

- `collect_*` → `data` queue
- `train_*` → `ml` queue
- `run_backtest` → `ml` queue
- `send_*` → `alerts` queue
- `process_news` → `data` queue
- `calculate_*` → `data` queue
- `scan_*` → `data` queue
- `generate_*` → `data` queue

## Configuration

### Environment Variables

Configure Celery using environment variables in your `.env` file:

```bash
# Celery Broker and Backend
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Worker Configuration
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000

# Task Limits
CELERY_TASK_TIME_LIMIT=3600        # 1 hour hard limit
CELERY_TASK_SOFT_TIME_LIMIT=3000   # 50 minutes soft limit
```

### Worker Pool Configuration

**Development (4 workers):**
```bash
celery -A stockiq.infrastructure.tasks worker --concurrency=4 --pool=solo
```

**Production (8 workers with autoscaling):**
```bash
celery -A stockiq.infrastructure.tasks worker --concurrency=8 --autoscale=16,8 --pool=prefork
```

**Queue-specific workers:**
```bash
# Data collection worker
celery -A stockiq.infrastructure.tasks worker --queues=data --concurrency=4

# ML processing worker
celery -A stockiq.infrastructure.tasks worker --queues=ml --concurrency=2

# Alert worker
celery -A stockiq.infrastructure.tasks worker --queues=alerts --concurrency=2
```

## Starting Celery

### Windows

**Start Worker:**
```bash
start-celery-worker.bat
```

**Start Beat Scheduler:**
```bash
start-celery-beat.bat
```

**Manual Start:**
```bash
# Worker
celery -A stockiq.infrastructure.tasks worker --loglevel=info --concurrency=4 --pool=solo

# Beat
celery -A stockiq.infrastructure.tasks beat --loglevel=info
```

### Linux/Mac

**Start Worker:**
```bash
celery -A stockiq.infrastructure.tasks worker --loglevel=info --concurrency=4
```

**Start Beat Scheduler:**
```bash
celery -A stockiq.infrastructure.tasks beat --loglevel=info
```

**Using Python Script:**
```bash
# Worker
python scripts/start_celery_worker.py worker --concurrency=4 --queues=data,ml,alerts

# Beat
python scripts/start_celery_worker.py beat
```

## Task Definitions

### Data Collection Tasks

#### `collect_market_data(tickers=None)`
Collects market data for specified tickers.
- **Queue**: `data`
- **Schedule**: Every 5 minutes during market hours
- **Retries**: 3 with 60s delay

#### `collect_latest_news(limit=100)`
Collects latest news from all configured sources.
- **Queue**: `data`
- **Schedule**: Every 30 minutes
- **Retries**: 3 with 60s delay

#### `scan_top_movers()`
Scans and identifies top gaining/losing stocks.
- **Queue**: `data`
- **Schedule**: Every 5 minutes during market hours
- **Retries**: 3 with 60s delay

#### `scan_penny_stocks()`
Scans for penny stocks with sudden gains.
- **Queue**: `data`
- **Schedule**: Every 2 minutes during market hours
- **Retries**: 3 with 60s delay

### ML & Prediction Tasks

#### `generate_daily_predictions()`
Generates next-day price predictions.
- **Queue**: `ml`
- **Schedule**: Daily at 7:00 AM ET
- **Retries**: 2 with 5min delay

#### `train_ml_model(ticker, model_type)`
Trains ML model for a specific ticker.
- **Queue**: `ml`
- **Time Limit**: 2 hours
- **Retries**: 2 with 10min delay

#### `run_backtest(strategy_id, start_date, end_date, initial_capital)`
Runs backtest simulation for a strategy.
- **Queue**: `ml`
- **Time Limit**: 2 hours
- **Retries**: 2 with 10min delay
- **Progress Tracking**: Updates task state during execution

### Alert Tasks

#### `send_alert(user_id, alert_type, message, data)`
Sends alert to a specific user.
- **Queue**: `alerts`
- **Retries**: 5 with 30s delay

#### `send_daily_reports()`
Sends daily market reports to all users.
- **Queue**: `alerts`
- **Schedule**: Daily at 8:00 AM ET
- **Retries**: 3 with 5min delay

## Beat Schedule

Celery Beat automatically executes these periodic tasks:

| Task | Schedule | Queue | Priority |
|------|----------|-------|----------|
| `collect_latest_news` | Every 30 minutes | data | 7 |
| `collect_market_data` | Every 5 min (9:30-4:00 ET) | data | 8 |
| `scan_top_movers` | Every 5 min (9:30-4:00 ET) | data | 7 |
| `scan_penny_stocks` | Every 2 min (9:30-4:00 ET) | data | 6 |
| `generate_daily_predictions` | Daily at 7:00 AM ET | ml | 9 |
| `send_daily_reports` | Daily at 8:00 AM ET | alerts | 8 |
| `analyze_news_sentiment` | Every 15 minutes | data | 6 |
| `track_model_performance` | Daily at 5:00 PM ET | ml | 5 |

## Task Retry Policy

All tasks implement automatic retry with exponential backoff:

- **Max Retries**: 3 (data tasks), 2 (ML tasks)
- **Retry Backoff**: Exponential with jitter
- **Max Backoff**: 10 minutes
- **Exceptions**: All exceptions trigger retry

Example retry timeline:
1. First retry: 60s
2. Second retry: 120s (2x)
3. Third retry: 240s (2x)

## Monitoring & Management

### Check Worker Status

```bash
# Active tasks
celery -A stockiq.infrastructure.tasks inspect active

# Registered tasks
celery -A stockiq.infrastructure.tasks inspect registered

# Worker statistics
celery -A stockiq.infrastructure.tasks inspect stats
```

### Check Scheduled Tasks

```bash
celery -A stockiq.infrastructure.tasks inspect scheduled
```

### Task Management

```python
from stockiq.infrastructure.tasks import (
    get_task_status,
    revoke_task,
    get_active_tasks,
    purge_queue
)

# Check task status
status = get_task_status(task_id)

# Cancel a task
revoke_task(task_id, terminate=True)

# Get active tasks
active = get_active_tasks()

# Purge a queue
purge_queue('data')
```

### Health Check

```python
from stockiq.infrastructure.tasks import health_check

# Run health check task
result = health_check.delay()
print(result.get())  # {"status": "healthy", ...}
```

## Performance Tuning

### Worker Concurrency

**Formula**: `concurrency = (2 * CPU_cores) + 1`

**Examples:**
- 4-core CPU: 8-9 workers
- 8-core CPU: 16-17 workers
- 16-core CPU: 32-33 workers

### Max Tasks Per Child

Restart workers after N tasks to prevent memory leaks:
- Development: 1000 tasks
- Production: 500-1000 tasks (depends on task memory usage)

### Prefetch Multiplier

Number of tasks to prefetch per worker:
- Default: 4
- High-throughput: 2
- Long-running tasks: 1

### Queue Priorities

Tasks have priority levels (0-9, higher = more priority):

- Priority 9: Critical (daily predictions)
- Priority 8: High (market data, daily reports)
- Priority 7: Medium-high (news, top movers)
- Priority 6: Medium (sentiment, penny stocks)
- Priority 5: Low (performance tracking)

## Error Handling

### Task Failures

1. **Automatic Retry**: Tasks retry automatically with exponential backoff
2. **Logging**: All failures are logged with context
3. **Dead Letter Queue**: Failed tasks after max retries are stored in result backend

### Worker Crashes

1. **Task Acknowledgment**: Tasks are acknowledged after completion (acks_late=True)
2. **Task Requeuing**: Unacknowledged tasks are requeued on worker crash
3. **Worker Restart**: Workers restart after N tasks to prevent memory leaks

## Security Considerations

### Message Serialization

- **Serializer**: JSON (secure, human-readable)
- **Accept**: Only JSON content
- **No pickle**: Pickle serialization is disabled for security

### Task Timeouts

- **Hard Limit**: 1 hour (configurable)
- **Soft Limit**: 50 minutes (raises exception)
- **ML Tasks**: 2 hours for training/backtesting

### Resource Limits

- **Max Memory**: Set via OS limits (ulimit)
- **Max Tasks**: 1000 per child process
- **Connection Pooling**: Managed by Redis

## Troubleshooting

### Worker Not Starting

```bash
# Check Redis connection
redis-cli -h localhost -p 6379 -n 1 ping

# Check broker URL
celery -A stockiq.infrastructure.tasks inspect ping

# Verbose logging
celery -A stockiq.infrastructure.tasks worker --loglevel=debug
```

### Tasks Not Executing

```bash
# Check if tasks are registered
celery -A stockiq.infrastructure.tasks inspect registered

# Check active workers
celery -A stockiq.infrastructure.tasks inspect active_queues

# Check task routing
celery -A stockiq.infrastructure.tasks inspect conf | grep task_routes
```

### High Memory Usage

1. Reduce `worker_max_tasks_per_child`
2. Reduce `worker_prefetch_multiplier`
3. Monitor task memory usage
4. Implement task cleanup

### Beat Not Scheduling

```bash
# Check beat status
celery -A stockiq.infrastructure.tasks inspect scheduled

# Restart beat
# Kill existing beat process and restart

# Check beat logs for errors
```

## Docker Deployment

See `docker-compose.yml` for containerized deployment:

```yaml
celery-worker:
  command: celery -A stockiq.infrastructure.tasks worker --loglevel=info --concurrency=4
  depends_on:
    - timescaledb
    - redis

celery-beat:
  command: celery -A stockiq.infrastructure.tasks beat --loglevel=info
  depends_on:
    - timescaledb
    - redis
```

## Next Steps

1. **Phase 0.2**: Implement data collection tasks
2. **Phase 0.3**: Implement alert tasks
3. **Phase 1**: Implement ML training tasks
4. **Phase 2**: Implement backtest tasks

## References

- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/documentation)
- [Task Queue Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html#best-practices)
