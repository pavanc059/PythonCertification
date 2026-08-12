# Redis 7.0+ Setup and Configuration Guide

**Task:** PHASE_0.1.2 - Redis Cache Setup  
**Requirements:** 22.1-22.4  
**Status:** ✅ Complete

## Overview

This guide covers Redis 7.0+ installation, configuration, and deployment for the StockIQ institutional-grade stock analyzer. Redis serves as:

- **Caching layer** for high-frequency market data
- **Pub/sub system** for real-time data distribution
- **Session storage** for user preferences
- **Message broker** for Celery task queue

## Table of Contents

1. [Development Setup](#development-setup)
2. [Production Deployment](#production-deployment)
3. [Redis Sentinel (High Availability)](#redis-sentinel-high-availability)
4. [Configuration Details](#configuration-details)
5. [Connection Pooling](#connection-pooling)
6. [Cache Key Patterns](#cache-key-patterns)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Troubleshooting](#troubleshooting)

---

## Development Setup

### Using Docker Compose (Recommended)

The easiest way to run Redis for development:

```bash
# Start Redis with all services
docker-compose up -d redis

# Check Redis status
docker-compose ps redis

# View Redis logs
docker-compose logs -f redis

# Connect to Redis CLI
docker exec -it stockiq-redis redis-cli

# Test connection
docker exec -it stockiq-redis redis-cli ping
# Expected output: PONG
```

### Manual Installation (Windows)

1. **Download Redis for Windows**
   - Visit: https://github.com/microsoftarchive/redis/releases
   - Download: `Redis-x64-7.0.x.msi`
   - Install to: `C:\Program Files\Redis`

2. **Configure Redis**
   ```cmd
   # Copy configuration
   copy redis\redis.conf "C:\Program Files\Redis\redis.conf"
   
   # Edit redis.conf and set working directory
   dir C:/Program Files/Redis/data
   ```

3. **Start Redis**
   ```cmd
   # As a service (recommended)
   redis-server --service-install "C:\Program Files\Redis\redis.conf"
   redis-server --service-start
   
   # Or run directly
   redis-server "C:\Program Files\Redis\redis.conf"
   ```

4. **Verify Installation**
   ```cmd
   redis-cli ping
   # Expected: PONG
   ```

### Manual Installation (Linux)

1. **Install Redis 7.0+**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install redis-server
   
   # Or compile from source for latest version
   wget http://download.redis.io/redis-stable.tar.gz
   tar xzf redis-stable.tar.gz
   cd redis-stable
   make
   sudo make install
   ```

2. **Configure Redis**
   ```bash
   # Copy configuration
   sudo cp redis/redis.conf /etc/redis/redis.conf
   
   # Create data directory
   sudo mkdir -p /var/lib/redis
   sudo chown redis:redis /var/lib/redis
   ```

3. **Start Redis**
   ```bash
   # Using systemd
   sudo systemctl start redis-server
   sudo systemctl enable redis-server
   
   # Check status
   sudo systemctl status redis-server
   ```

4. **Verify Installation**
   ```bash
   redis-cli ping
   # Expected: PONG
   ```

---

## Production Deployment

### Production Configuration

Use the production-optimized configuration:

```bash
# Copy production config
cp redis/redis-production.conf /etc/redis/redis.conf

# Set Redis password
export REDIS_PASSWORD=$(openssl rand -base64 32)

# Update config with password
sed -i "s/\${REDIS_PASSWORD}/$REDIS_PASSWORD/g" /etc/redis/redis.conf
```

### Key Production Settings

The `redis-production.conf` file includes:

**Persistence:**
- RDB snapshots: 15min (1 key), 5min (10 keys), 1min (10k keys)
- AOF enabled with `everysec` fsync
- Hybrid RDB-AOF format for fast restarts

**Memory Management:**
- Limit: 4GB (adjust based on server)
- Eviction: `allkeys-lru`
- Active defragmentation enabled

**Performance:**
- 8 I/O threads (adjust to CPU cores / 2)
- Lazy freeing enabled
- Jemalloc background thread

**Security:**
- Password authentication required
- Dangerous commands disabled
- Protected mode enabled

### Environment Variables

Set in `.env` or environment:

```bash
# Redis connection
REDIS_URL=redis://:password@host:6379/0
REDIS_PASSWORD=your_strong_password_here
REDIS_MAX_CONNECTIONS=50

# Celery (different DB numbers)
CELERY_BROKER_URL=redis://:password@host:6379/1
CELERY_RESULT_BACKEND=redis://:password@host:6379/2
```

### Docker Production Deployment

1. **Update docker-compose.yml for production:**

```yaml
redis:
  image: redis:7-alpine
  container_name: stockiq-redis
  command: redis-server /usr/local/etc/redis/redis-production.conf
  ports:
    - "127.0.0.1:6379:6379"  # Bind to localhost only
  volumes:
    - redis_data:/data
    - ./redis/redis-production.conf:/usr/local/etc/redis/redis-production.conf:ro
  environment:
    - REDIS_PASSWORD=${REDIS_PASSWORD}
  restart: always
  deploy:
    resources:
      limits:
        memory: 4G
      reservations:
        memory: 2G
```

2. **Start production services:**

```bash
# With password authentication
export REDIS_PASSWORD=$(openssl rand -base64 32)
docker-compose up -d redis

# Verify
docker exec -it stockiq-redis redis-cli -a $REDIS_PASSWORD ping
```

---

## Redis Sentinel (High Availability)

Redis Sentinel provides automatic failover and high availability for production deployments.

### Architecture

```
┌─────────────────┐
│   Application   │
│   (StockIQ)     │
└────────┬────────┘
         │ (connects via Sentinel)
         │
    ┌────┴────┬─────────────┬─────────────┐
    │         │             │             │
┌───▼───┐ ┌───▼───┐    ┌───▼───┐    ┌───▼───┐
│Sentinel│ │Sentinel│    │Sentinel│    │ Redis │
│   1    │ │   2    │    │   3    │    │ Master│
└────────┘ └────────┘    └────────┘    └───┬───┘
                                            │
                                ┌───────────┴───────────┐
                                │                       │
                           ┌────▼────┐            ┌────▼────┐
                           │  Redis  │            │  Redis  │
                           │ Replica │            │ Replica │
                           └─────────┘            └─────────┘
```

### Setup (Docker Compose)

1. **Create `docker-compose.sentinel.yml`:**

```yaml
version: '3.8'

services:
  redis-master:
    image: redis:7-alpine
    container_name: redis-master
    command: redis-server /usr/local/etc/redis/redis-production.conf
    volumes:
      - ./redis/redis-production.conf:/usr/local/etc/redis/redis-production.conf:ro
      - redis_master_data:/data
    networks:
      - redis-ha

  redis-replica-1:
    image: redis:7-alpine
    container_name: redis-replica-1
    command: redis-server /usr/local/etc/redis/redis-production.conf --replicaof redis-master 6379
    volumes:
      - ./redis/redis-production.conf:/usr/local/etc/redis/redis-production.conf:ro
      - redis_replica_1_data:/data
    depends_on:
      - redis-master
    networks:
      - redis-ha

  redis-replica-2:
    image: redis:7-alpine
    container_name: redis-replica-2
    command: redis-server /usr/local/etc/redis/redis-production.conf --replicaof redis-master 6379
    volumes:
      - ./redis/redis-production.conf:/usr/local/etc/redis/redis-production.conf:ro
      - redis_replica_2_data:/data
    depends_on:
      - redis-master
    networks:
      - redis-ha

  sentinel-1:
    image: redis:7-alpine
    container_name: sentinel-1
    command: redis-sentinel /usr/local/etc/redis/sentinel.conf
    volumes:
      - ./redis/sentinel.conf:/usr/local/etc/redis/sentinel.conf:ro
    depends_on:
      - redis-master
    networks:
      - redis-ha

  sentinel-2:
    image: redis:7-alpine
    container_name: sentinel-2
    command: redis-sentinel /usr/local/etc/redis/sentinel.conf
    volumes:
      - ./redis/sentinel.conf:/usr/local/etc/redis/sentinel.conf:ro
    depends_on:
      - redis-master
    networks:
      - redis-ha

  sentinel-3:
    image: redis:7-alpine
    container_name: sentinel-3
    command: redis-sentinel /usr/local/etc/redis/sentinel.conf
    volumes:
      - ./redis/sentinel.conf:/usr/local/etc/redis/sentinel.conf:ro
    depends_on:
      - redis-master
    networks:
      - redis-ha

volumes:
  redis_master_data:
  redis_replica_1_data:
  redis_replica_2_data:

networks:
  redis-ha:
    driver: bridge
```

2. **Update application to use Sentinel:**

```python
from redis.sentinel import Sentinel

# Configure Sentinel
sentinel = Sentinel([
    ('sentinel-1', 26379),
    ('sentinel-2', 26379),
    ('sentinel-3', 26379)
], socket_timeout=0.5)

# Get master connection (for writes)
master = sentinel.master_for('stockiq-master', socket_timeout=0.5)

# Get slave connection (for reads)
slave = sentinel.slave_for('stockiq-master', socket_timeout=0.5)
```

3. **Start Sentinel cluster:**

```bash
docker-compose -f docker-compose.sentinel.yml up -d

# Check Sentinel status
docker exec -it sentinel-1 redis-cli -p 26379 sentinel masters
docker exec -it sentinel-1 redis-cli -p 26379 sentinel slaves stockiq-master
```

### Sentinel Configuration

Key settings in `sentinel.conf`:

- **Quorum**: 2 (minimum sentinels to agree on failover)
- **Down-after-milliseconds**: 5000 (consider master down after 5s)
- **Failover-timeout**: 60000 (60s timeout for failover)
- **Parallel-syncs**: 1 (replicas to sync simultaneously)

### Testing Failover

```bash
# Simulate master failure
docker stop redis-master

# Watch sentinel promote replica
docker exec -it sentinel-1 redis-cli -p 26379 sentinel get-master-addr-by-name stockiq-master

# Application should automatically reconnect to new master
```

---

## Configuration Details

### Persistence Strategy: RDB + AOF

**RDB (Redis Database Backup):**
- Point-in-time snapshots
- Compact file format
- Fast restarts
- Good for backups

**AOF (Append Only File):**
- Log of every write operation
- More durable (less data loss)
- Automatic compaction
- Slower restarts

**Hybrid Mode (Best of Both):**
```conf
# Enable both
save 900 1
appendonly yes
aof-use-rdb-preamble yes
```

### Memory Eviction Policies

```conf
maxmemory 512mb
maxmemory-policy allkeys-lru
```

**Available policies:**
- `allkeys-lru`: Evict any key using LRU (recommended for cache)
- `volatile-lru`: Evict keys with TTL using LRU
- `allkeys-lfu`: Evict any key using LFU (frequency-based)
- `volatile-lfu`: Evict keys with TTL using LFU
- `allkeys-random`: Evict random key
- `volatile-random`: Evict random key with TTL
- `volatile-ttl`: Evict key with shortest TTL
- `noeviction`: Return error when memory full

**StockIQ uses `allkeys-lru`** because:
- All data is cache-able
- LRU works well for time-series data
- Balances performance and memory usage

### Connection Pooling

Configured in `stockiq/infrastructure/cache.py`:

```python
_connection_pool = ConnectionPool.from_url(
    settings.redis_url,
    max_connections=50,  # Adjust based on load
    decode_responses=False,
)
```

**Benefits:**
- Reuse connections (no connection overhead)
- Limit concurrent connections
- Automatic connection recovery
- Thread-safe operations

---

## Cache Key Patterns

See `CACHE_KEY_PATTERNS.md` for complete reference.

### Key Categories and TTLs

| Category | Pattern | TTL | Example |
|----------|---------|-----|---------|
| Real-time prices | `price:{ticker}:latest` | 30s | `price:AAPL:latest` |
| Historical prices | `price:{ticker}:history:{timeframe}` | 5min | `price:AAPL:history:1d` |
| News | `news:ticker:{ticker}:{hours}` | 1hr | `news:ticker:AAPL:24` |
| Sentiment | `sentiment:{ticker}:latest` | 15min | `sentiment:AAPL:latest` |
| Predictions | `prediction:{ticker}:{date}` | 24hr | `prediction:AAPL:2024-01-15` |
| Top movers | `movers:gainers:{date}` | 5min | `movers:gainers:2024-01-15` |
| Penny stocks | `penny:momentum:{ticker}` | 2min | `penny:momentum:XYZZ` |

### Usage Example

```python
from stockiq.infrastructure.cache import get_cache, CacheKeyPatterns

cache = get_cache()

# Store price with automatic TTL
key = CacheKeyPatterns.format_key(
    CacheKeyPatterns.PRICE_LATEST,
    ticker="AAPL"
)
cache.set_with_pattern_ttl(key, price_data)

# Retrieve price
price = cache.get(key)
```

---

## Monitoring and Maintenance

### Health Checks

```bash
# Check Redis is running
redis-cli ping

# Check memory usage
redis-cli info memory

# Check connected clients
redis-cli client list

# Check slow queries
redis-cli slowlog get 10

# Check key count
redis-cli dbsize
```

### Key Metrics to Monitor

1. **Memory Usage**
   ```bash
   redis-cli info memory | grep used_memory_human
   ```

2. **Hit Rate**
   ```bash
   redis-cli info stats | grep keyspace
   ```

3. **Connected Clients**
   ```bash
   redis-cli info clients | grep connected_clients
   ```

4. **Operations Per Second**
   ```bash
   redis-cli info stats | grep instantaneous_ops_per_sec
   ```

5. **Evicted Keys**
   ```bash
   redis-cli info stats | grep evicted_keys
   ```

### Performance Tuning

**Optimize for throughput:**
```conf
io-threads 8
io-threads-do-reads yes
lazyfree-lazy-eviction yes
```

**Optimize for latency:**
```conf
appendfsync no  # Disable fsync (less durable)
hz 10
```

**Optimize for memory:**
```conf
activedefrag yes
maxmemory-policy volatile-lru
```

### Backup and Recovery

**Create backup:**
```bash
# RDB backup
redis-cli BGSAVE

# AOF rewrite
redis-cli BGREWRITEAOF

# Copy files
cp /data/dump.rdb /backup/
cp /data/appendonly.aof /backup/
```

**Restore from backup:**
```bash
# Stop Redis
systemctl stop redis-server

# Restore files
cp /backup/dump.rdb /var/lib/redis/
cp /backup/appendonly.aof /var/lib/redis/

# Start Redis
systemctl start redis-server
```

---

## Troubleshooting

### Common Issues

**1. Connection refused**
```bash
# Check Redis is running
systemctl status redis-server
docker ps | grep redis

# Check port binding
netstat -tlnp | grep 6379

# Check firewall
sudo ufw allow 6379
```

**2. Authentication failed**
```bash
# Check password
redis-cli -a your_password ping

# Update application config
export REDIS_PASSWORD=your_password
```

**3. Out of memory**
```bash
# Check memory usage
redis-cli info memory

# Increase maxmemory
redis-cli CONFIG SET maxmemory 1gb

# Or flush data
redis-cli FLUSHALL  # WARNING: Deletes all data!
```

**4. Slow performance**
```bash
# Check slow queries
redis-cli SLOWLOG GET 10

# Check latency
redis-cli --latency

# Check fragmentation
redis-cli info memory | grep fragmentation_ratio
```

**5. High memory fragmentation**
```bash
# Enable active defragmentation
redis-cli CONFIG SET activedefrag yes

# Or restart Redis (clears fragmentation)
systemctl restart redis-server
```

### Debugging Commands

```bash
# Monitor all commands in real-time
redis-cli MONITOR

# Get Redis configuration
redis-cli CONFIG GET '*'

# Check replication status
redis-cli INFO replication

# Latency diagnostics
redis-cli --latency-history

# Check used commands
redis-cli INFO commandstats
```

### Logs

**View logs:**
```bash
# Docker
docker logs stockiq-redis

# Systemd
sudo journalctl -u redis-server -f

# Direct
tail -f /var/log/redis/redis-server.log
```

---

## Security Best Practices

1. **Use strong passwords:**
   ```bash
   export REDIS_PASSWORD=$(openssl rand -base64 32)
   ```

2. **Bind to localhost only (if possible):**
   ```conf
   bind 127.0.0.1
   ```

3. **Disable dangerous commands:**
   ```conf
   rename-command FLUSHDB ""
   rename-command FLUSHALL ""
   rename-command CONFIG ""
   ```

4. **Use TLS/SSL (production):**
   ```conf
   port 0
   tls-port 6379
   tls-cert-file /path/to/redis.crt
   tls-key-file /path/to/redis.key
   tls-ca-cert-file /path/to/ca.crt
   ```

5. **Enable protected mode:**
   ```conf
   protected-mode yes
   ```

6. **Use firewall rules:**
   ```bash
   # Allow only application server
   sudo ufw allow from 10.0.1.100 to any port 6379
   ```

---

## Verification

### Test Connection from Application

```python
from stockiq.infrastructure.cache import get_cache

# Test basic operations
cache = get_cache()

# Ping
assert cache.ping()

# Set/Get
cache.set("test:key", "value", ttl=60)
value = cache.get("test:key")
assert value == "value"

# Delete
cache.delete("test:key")

# Get info
info = cache.get_info()
print(f"Redis version: {info['redis_version']}")
print(f"Used memory: {info['used_memory_human']}")
print(f"Connected clients: {info['connected_clients']}")
```

### Run Verification Script

```bash
# Test Redis connectivity
python scripts/verify_redis.py

# Expected output:
# ✓ Redis connection successful
# ✓ Redis version: 7.0.x
# ✓ Cache operations working
# ✓ Connection pooling active
```

---

## Next Steps

After completing Redis setup:

1. ✅ Redis 7.0+ installed and configured
2. ✅ Connection pooling implemented
3. ✅ Persistence (RDB + AOF) enabled
4. ✅ Memory limits and eviction configured
5. ✅ Cache key patterns defined
6. ⏭️ Proceed to PHASE_0.1.3: Celery Task Queue Setup
7. ⏭️ Implement data collection tasks using Redis cache

---

## References

- [Redis Official Documentation](https://redis.io/documentation)
- [Redis Persistence](https://redis.io/topics/persistence)
- [Redis Sentinel](https://redis.io/topics/sentinel)
- [Redis Best Practices](https://redis.io/topics/best-practices)
- [Redis Security](https://redis.io/topics/security)
- Requirements 22.1-22.4 in `requirements.md`
- Task details in `tasks.md` PHASE_0.1.2

---

**Status:** ✅ Redis Setup Complete  
**Next Task:** PHASE_0.1.3 - Celery Task Queue Setup  
**Last Updated:** 2024-01-15
