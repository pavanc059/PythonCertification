"""
Script to start Celery worker with proper configuration.

This script provides a convenient way to start Celery workers with
recommended settings for development and production environments.
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def start_worker(
    concurrency=4,
    queues=None,
    loglevel="info",
    pool="prefork",
    hostname=None,
):
    """
    Start a Celery worker with specified configuration.
    
    Args:
        concurrency: Number of worker processes
        queues: Comma-separated list of queues to consume from
        loglevel: Logging level (debug, info, warning, error, critical)
        pool: Worker pool type (prefork, solo, gevent, eventlet)
        hostname: Custom hostname for the worker
    """
    from stockiq.infrastructure.tasks import celery_app
    
    # Build worker arguments
    argv = [
        "worker",
        f"--loglevel={loglevel}",
        f"--concurrency={concurrency}",
        f"--pool={pool}",
    ]
    
    if queues:
        argv.append(f"--queues={queues}")
    else:
        # Default: consume from all queues
        argv.append("--queues=data,ml,alerts,celery")
    
    if hostname:
        argv.append(f"--hostname={hostname}")
    
    # Add max tasks per child to prevent memory leaks
    argv.append("--max-tasks-per-child=1000")
    
    # Add autoscale support for dynamic worker adjustment
    # Format: autoscale=max_concurrency,min_concurrency
    max_workers = concurrency * 2
    argv.append(f"--autoscale={max_workers},{concurrency}")
    
    print(f"Starting Celery worker with arguments: {' '.join(argv)}")
    print(f"Consuming from queues: {queues or 'data,ml,alerts,celery'}")
    print(f"Worker concurrency: {concurrency}")
    print(f"Pool type: {pool}")
    print("-" * 60)
    
    # Start the worker
    celery_app.worker_main(argv)


def start_beat(loglevel="info"):
    """
    Start Celery Beat scheduler for periodic tasks.
    
    Args:
        loglevel: Logging level
    """
    from stockiq.infrastructure.tasks import celery_app
    
    argv = [
        "beat",
        f"--loglevel={loglevel}",
    ]
    
    print(f"Starting Celery Beat scheduler")
    print(f"Log level: {loglevel}")
    print("-" * 60)
    
    celery_app.worker_main(argv)


def main():
    parser = argparse.ArgumentParser(
        description="Start Celery worker or beat scheduler"
    )
    
    parser.add_argument(
        "mode",
        choices=["worker", "beat"],
        help="Start worker or beat scheduler"
    )
    
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Number of worker processes (default: 4)"
    )
    
    parser.add_argument(
        "--queues",
        type=str,
        default=None,
        help="Comma-separated list of queues (default: all queues)"
    )
    
    parser.add_argument(
        "--loglevel",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Logging level (default: info)"
    )
    
    parser.add_argument(
        "--pool",
        choices=["prefork", "solo", "gevent", "eventlet"],
        default="prefork",
        help="Worker pool type (default: prefork)"
    )
    
    parser.add_argument(
        "--hostname",
        type=str,
        default=None,
        help="Custom hostname for the worker"
    )
    
    args = parser.parse_args()
    
    if args.mode == "worker":
        start_worker(
            concurrency=args.concurrency,
            queues=args.queues,
            loglevel=args.loglevel,
            pool=args.pool,
            hostname=args.hostname,
        )
    elif args.mode == "beat":
        start_beat(loglevel=args.loglevel)


if __name__ == "__main__":
    main()
