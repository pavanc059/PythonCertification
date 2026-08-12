# Deployment Guide

**Version:** 2.0  
**Last Updated:** 2024

This guide covers deploying the StockIQ platform using Docker Compose and Kubernetes.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Docker Compose Deployment](#docker-compose-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Redis Configuration](#redis-configuration)
- [Celery Configuration](#celery-configuration)
- [Production Considerations](#production-considerations)
- [Monitoring and Logging](#monitoring-and-logging)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum Requirements:**
- CPU: 4 cores
- RAM: 8 GB
- Disk: 50 GB SSD
- OS: Linux (Ubuntu 20.04+), macOS, or Windows with WSL2

**Recommended for Production:**
- CPU: 8+ cores
- RAM: 16+ GB
- Disk: 200+ GB SSD
- OS: Linux (Ubuntu 22.04 LTS)

### Software Requirements

- **Docker**: 20.10+ or Docker Desktop
- **Docker Compose**: 2.0+
- **kubectl**: 1.24+ (for Kubernetes deployment)
- **Git**: 2.30+

---

## Docker Compose Deployment

Docker Compose is the recommended deployment method for single-server installations.

### Quick Start

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/stockiq.git
cd stockiq
```

2. **Configure environment variables**

```bash
cp .env.example .env
nano .env  # Edit with your configuration
```

3. **Start services**

```bash
docker-compose up -d
```

4. **Verify deployment**

```bash
docker-compose ps
docker-compose logs -f
```

5. **Access application**

- Web Interface: http://localhost:8501
- PostgreSQL: localhost:5432
- Redis: localhost:6379


### Docker Compose Architecture

The `docker-compose.yml` file defines the following services:

```yaml
services:
  - timescaledb    # PostgreSQL + TimescaleDB extension
  - redis          # Cache and message broker
  - celery-worker  # Background task processor
  - celery-beat    # Task scheduler
  - web            # Streamlit web application
  - db-init        # Database initialization (runs once)
```

### Service Configuration

#### TimescaleDB Service

```yaml
timescaledb:
  image: timescale/timescaledb:latest-pg14
  ports:
    - "5432:5432"
  environment:
    POSTGRES_DB: stockiq
    POSTGRES_USER: stockiq
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  volumes:
    - timescaledb_data:/var/lib/postgresql/data
    - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
```

**Configuration Options:**
- `POSTGRES_PASSWORD`: Database password (set in .env)
- `POSTGRES_DB`: Database name (default: stockiq)
- `POSTGRES_USER`: Database user (default: stockiq)

#### Redis Service

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  command: redis-server /usr/local/etc/redis/redis.conf
  volumes:
    - redis_data:/data
    - ./redis/redis.conf:/usr/local/etc/redis/redis.conf:ro
```

**Configuration Options:**
- Custom redis.conf for production settings
- Persistence enabled with AOF
- Memory limits configured in redis.conf

#### Web Application Service

```yaml
web:
  build: .
  ports:
    - "8501:8501"
  command: streamlit run app.py --server.port=8501 --server.address=0.0.0.0
  environment:
    DATABASE_URL: postgresql://stockiq:${POSTGRES_PASSWORD}@timescaledb:5432/stockiq
    REDIS_URL: redis://redis:6379/0
    NEWSAPI_KEY: ${NEWSAPI_KEY}
    FINNHUB_API_KEY: ${FINNHUB_API_KEY}
```

### Scaling Services

Scale Celery workers for increased throughput:

```bash
docker-compose up -d --scale celery-worker=4
```


### Management Commands

**Start all services:**
```bash
docker-compose up -d
```

**Stop all services:**
```bash
docker-compose down
```

**View logs:**
```bash
docker-compose logs -f [service_name]
docker-compose logs -f web
docker-compose logs -f celery-worker
```

**Restart a service:**
```bash
docker-compose restart web
```

**Rebuild images:**
```bash
docker-compose build
docker-compose up -d
```

**Execute commands in containers:**
```bash
docker-compose exec web python scripts/init_db.py
docker-compose exec timescaledb psql -U stockiq -d stockiq
```

---

## Kubernetes Deployment

For production deployments requiring high availability and scalability.

### Kubernetes Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured
- Helm 3.0+ (optional but recommended)
- Persistent volume support
- LoadBalancer or Ingress controller

### Architecture Overview

```
Kubernetes Cluster
├── Namespace: stockiq
├── StatefulSet: timescaledb (1 replica)
├── Deployment: redis (1 replica)
├── Deployment: celery-worker (3+ replicas)
├── Deployment: celery-beat (1 replica)
├── Deployment: web (2+ replicas)
├── Service: timescaledb-service (ClusterIP)
├── Service: redis-service (ClusterIP)
├── Service: web-service (LoadBalancer)
├── PersistentVolumeClaim: timescaledb-pvc
├── PersistentVolumeClaim: redis-pvc
├── ConfigMap: stockiq-config
└── Secret: stockiq-secrets
```

### Kubernetes Manifests

Create a `k8s/` directory with the following manifests:

#### 1. Namespace

**File:** `k8s/namespace.yaml`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: stockiq
```


#### 2. Secrets

**File:** `k8s/secrets.yaml`

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: stockiq-secrets
  namespace: stockiq
type: Opaque
stringData:
  postgres-password: "your_secure_password"
  redis-password: "your_redis_password"
  newsapi-key: "your_newsapi_key"
  finnhub-api-key: "your_finnhub_key"
  alphavantage-api-key: "your_alphavantage_key"
```

**Create from command line:**
```bash
kubectl create secret generic stockiq-secrets \
  --from-literal=postgres-password=your_password \
  --from-literal=newsapi-key=your_key \
  --namespace=stockiq
```

#### 3. ConfigMap

**File:** `k8s/configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: stockiq-config
  namespace: stockiq
data:
  LOG_LEVEL: "INFO"
  CACHE_TTL_DEFAULT: "3600"
  DATABASE_NAME: "stockiq"
  DATABASE_USER: "stockiq"
```

#### 4. Persistent Volumes

**File:** `k8s/persistent-volumes.yaml`

```yaml
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: timescaledb-pvc
  namespace: stockiq
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
  storageClassName: fast-ssd
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: stockiq
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: fast-ssd
```


#### 5. TimescaleDB StatefulSet

**File:** `k8s/timescaledb-statefulset.yaml`

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: timescaledb
  namespace: stockiq
spec:
  serviceName: timescaledb-service
  replicas: 1
  selector:
    matchLabels:
      app: timescaledb
  template:
    metadata:
      labels:
        app: timescaledb
    spec:
      containers:
      - name: timescaledb
        image: timescale/timescaledb:latest-pg14
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: POSTGRES_DB
          valueFrom:
            configMapKeyRef:
              name: stockiq-config
              key: DATABASE_NAME
        - name: POSTGRES_USER
          valueFrom:
            configMapKeyRef:
              name: stockiq-config
              key: DATABASE_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: stockiq-secrets
              key: postgres-password
        volumeMounts:
        - name: timescaledb-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
  volumeClaimTemplates:
  - metadata:
      name: timescaledb-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 100Gi
---
apiVersion: v1
kind: Service
metadata:
  name: timescaledb-service
  namespace: stockiq
spec:
  selector:
    app: timescaledb
  ports:
  - port: 5432
    targetPort: 5432
  clusterIP: None
```


#### 6. Web Application Deployment

**File:** `k8s/web-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: stockiq
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: ghcr.io/yourusername/stockiq:latest
        command: ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
        ports:
        - containerPort: 8501
        env:
        - name: DATABASE_URL
          value: "postgresql://$(DATABASE_USER):$(POSTGRES_PASSWORD)@timescaledb-service:5432/$(DATABASE_NAME)"
        - name: DATABASE_USER
          valueFrom:
            configMapKeyRef:
              name: stockiq-config
              key: DATABASE_USER
        - name: DATABASE_NAME
          valueFrom:
            configMapKeyRef:
              name: stockiq-config
              key: DATABASE_NAME
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: stockiq-secrets
              key: postgres-password
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        - name: NEWSAPI_KEY
          valueFrom:
            secretKeyRef:
              name: stockiq-secrets
              key: newsapi-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
---
apiVersion: v1
kind: Service
metadata:
  name: web-service
  namespace: stockiq
spec:
  type: LoadBalancer
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 8501
```


#### 7. Celery Worker Deployment

**File:** `k8s/celery-worker-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
  namespace: stockiq
spec:
  replicas: 4
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
      - name: celery-worker
        image: ghcr.io/yourusername/stockiq:latest
        command: ["celery", "-A", "stockiq.infrastructure.tasks", "worker", "--loglevel=info", "--concurrency=4"]
        env:
        - name: DATABASE_URL
          value: "postgresql://$(DATABASE_USER):$(POSTGRES_PASSWORD)@timescaledb-service:5432/$(DATABASE_NAME)"
        - name: DATABASE_USER
          valueFrom:
            configMapKeyRef:
              name: stockiq-config
              key: DATABASE_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: stockiq-secrets
              key: postgres-password
        - name: CELERY_BROKER_URL
          value: "redis://redis-service:6379/1"
        - name: CELERY_RESULT_BACKEND
          value: "redis://redis-service:6379/2"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
```

### Deploy to Kubernetes

1. **Create namespace and resources:**

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/persistent-volumes.yaml
```

2. **Deploy database and cache:**

```bash
kubectl apply -f k8s/timescaledb-statefulset.yaml
kubectl apply -f k8s/redis-deployment.yaml
```

3. **Wait for database to be ready:**

```bash
kubectl wait --for=condition=ready pod -l app=timescaledb -n stockiq --timeout=300s
```

4. **Initialize database:**

```bash
kubectl exec -it timescaledb-0 -n stockiq -- psql -U stockiq -d stockiq -f /docker-entrypoint-initdb.d/init.sql
```

5. **Deploy application services:**

```bash
kubectl apply -f k8s/web-deployment.yaml
kubectl apply -f k8s/celery-worker-deployment.yaml
kubectl apply -f k8s/celery-beat-deployment.yaml
```

6. **Verify deployment:**

```bash
kubectl get pods -n stockiq
kubectl get services -n stockiq
```


---

## Environment Configuration

### Required Environment Variables

Create a `.env` file with the following variables:

```bash
# Database Configuration
POSTGRES_PASSWORD=your_secure_password_here
DATABASE_URL=postgresql://stockiq:your_password@timescaledb:5432/stockiq

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=  # Optional, leave empty if no password

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# API Keys (Required)
NEWSAPI_KEY=your_newsapi_key
FINNHUB_API_KEY=your_finnhub_key

# API Keys (Optional)
ALPHAVANTAGE_API_KEY=your_alphavantage_key

# Application Configuration
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
CACHE_TTL_DEFAULT=3600  # Default cache TTL in seconds
PREDICTION_CONFIDENCE_THRESHOLD=0.6  # Minimum prediction confidence

# Feature Flags
ENABLE_WEBSOCKET_STREAMING=true
ENABLE_ML_PREDICTIONS=true
ENABLE_NEWS_ANALYSIS=true
ENABLE_PENNY_STOCK_SCANNER=true
```

### Obtaining API Keys

#### NewsAPI (newsapi.org)

1. Visit https://newsapi.org/register
2. Sign up for a free account
3. Copy your API key
4. Free tier: 1,000 requests/day

#### Finnhub (finnhub.io)

1. Visit https://finnhub.io/register
2. Create a free account
3. Get API key from dashboard
4. Free tier: 60 requests/minute

#### Alpha Vantage (alphavantage.co)

1. Visit https://www.alphavantage.co/support/#api-key
2. Request a free API key
3. Free tier: 5 requests/minute

---

## Database Setup

### Manual Database Initialization

If using an external PostgreSQL instance:

```bash
# Connect to PostgreSQL
psql -h localhost -U postgres

# Create database and user
CREATE DATABASE stockiq;
CREATE USER stockiq WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE stockiq TO stockiq;

# Enable TimescaleDB extension
\c stockiq
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

### Run Initialization Script

```bash
python scripts/init_db.py
```

This script:
- Creates all required tables
- Sets up TimescaleDB hypertables
- Creates indexes
- Initializes continuous aggregates
- Sets up partitioning


### Database Schema

Key tables:

- `prices` - Historical and real-time price data (hypertable)
- `news_articles` - News articles and sentiment
- `predictions` - ML prediction history
- `portfolio` - User portfolio holdings
- `alerts` - Alert configurations
- `penny_stocks` - Penny stock tracking
- `market_overview` - Market indices and sector performance

### Database Backup

**Create backup:**
```bash
docker-compose exec timescaledb pg_dump -U stockiq stockiq > backup.sql
```

**Restore from backup:**
```bash
cat backup.sql | docker-compose exec -T timescaledb psql -U stockiq stockiq
```

---

## Redis Configuration

### Redis Configuration File

**File:** `redis/redis.conf`

```conf
# Memory
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec

# Performance
tcp-backlog 511
timeout 0
tcp-keepalive 300

# Security
# requirepass your_redis_password  # Uncomment for password
protected-mode yes
```

### Redis Database Allocation

- DB 0: Application cache
- DB 1: Celery broker
- DB 2: Celery results
- DB 3: Session storage

### Redis Monitoring

```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli

# Monitor commands
MONITOR

# Get info
INFO

# Check memory usage
MEMORY STATS
```

---

## Celery Configuration

### Celery Worker Configuration

**File:** `stockiq/infrastructure/tasks.py`

```python
celery_app = Celery(
    'stockiq',
    broker=os.getenv('CELERY_BROKER_URL'),
    backend=os.getenv('CELERY_RESULT_BACKEND')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
```


### Scheduled Tasks (Celery Beat)

Key scheduled tasks:

- **collect_top_movers**: Every 5 minutes (market hours)
- **collect_news**: Every 10 minutes
- **update_penny_stocks**: Every 2 minutes (market hours)
- **generate_daily_predictions**: 7:30 AM ET daily
- **generate_daily_report**: 8:00 AM ET daily
- **cleanup_old_data**: 2:00 AM daily

### Monitoring Celery

```bash
# View worker status
celery -A stockiq.infrastructure.tasks inspect active

# View scheduled tasks
celery -A stockiq.infrastructure.tasks inspect scheduled

# Worker statistics
celery -A stockiq.infrastructure.tasks inspect stats
```

---

## Production Considerations

### Security Best Practices

1. **Use strong passwords**
   - Generate secure passwords for PostgreSQL and Redis
   - Store secrets in environment variables or secret management systems

2. **Enable SSL/TLS**
   - Configure SSL for PostgreSQL connections
   - Use TLS for Redis connections
   - Deploy web interface behind HTTPS

3. **Network security**
   - Use Docker networks or Kubernetes network policies
   - Restrict database access to application services only
   - Use firewall rules to limit exposure

4. **Regular updates**
   - Keep Docker images updated
   - Update dependencies regularly
   - Monitor security advisories

### Performance Tuning

#### PostgreSQL Tuning

Edit `postgresql.conf`:

```conf
# Memory
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
work_mem = 256MB

# Connections
max_connections = 200

# Checkpoints
checkpoint_completion_target = 0.9
wal_buffers = 16MB
```

#### Redis Tuning

```conf
# Increase max clients
maxclients 10000

# Enable lazy freeing
lazyfree-lazy-eviction yes
lazyfree-lazy-expire yes

# Disable persistence for cache-only usage
save ""
appendonly no
```

### Scaling Strategy

**Horizontal Scaling:**

1. Scale web instances:
   ```bash
   docker-compose up -d --scale web=4
   ```

2. Scale Celery workers:
   ```bash
   docker-compose up -d --scale celery-worker=8
   ```

**Vertical Scaling:**

- Increase resource limits in docker-compose.yml
- Adjust PostgreSQL shared_buffers
- Increase Redis maxmemory


---

## Monitoring and Logging

### Log Collection

Logs are stored in `./logs/` directory:

- `app.log` - Application logs
- `celery.log` - Celery worker logs
- `error.log` - Error logs

### Structured Logging

StockIQ uses structured JSON logging:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "module": "stockiq.data.collectors.market",
  "message": "Collected price data for AAPL",
  "ticker": "AAPL",
  "price": 175.50,
  "duration_ms": 234
}
```

### Monitoring Tools

**Prometheus + Grafana (Recommended):**

Add to docker-compose.yml:

```yaml
prometheus:
  image: prom/prometheus
  volumes:
    - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

**Health Checks:**

- Web: http://localhost:8501/_stcore/health
- Database: `pg_isready -h localhost -U stockiq`
- Redis: `redis-cli ping`

---

## Backup and Recovery

### Database Backup Strategy

**Automated Daily Backups:**

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T timescaledb pg_dump -U stockiq stockiq | gzip > backups/stockiq_$DATE.sql.gz

# Keep last 30 days
find backups/ -name "stockiq_*.sql.gz" -mtime +30 -delete
```

Add to crontab:
```bash
0 2 * * * /path/to/backup.sh
```

**Restore Procedure:**

```bash
# Stop services
docker-compose stop web celery-worker celery-beat

# Drop and recreate database
docker-compose exec timescaledb psql -U postgres -c "DROP DATABASE stockiq;"
docker-compose exec timescaledb psql -U postgres -c "CREATE DATABASE stockiq;"

# Restore from backup
gunzip -c backups/stockiq_20240115.sql.gz | docker-compose exec -T timescaledb psql -U stockiq stockiq

# Restart services
docker-compose start web celery-worker celery-beat
```

### Disaster Recovery

1. **Regular Testing**
   - Test backups monthly
   - Document recovery time

2. **Off-site Backups**
   - Upload to S3, Google Cloud Storage, or Azure Blob
   - Encrypt backups at rest

3. **Backup Verification**
   - Automated backup integrity checks
   - Restore tests in staging environment

---

## Troubleshooting

### Common Issues

#### Port Already in Use

**Problem:** Port 5432 or 8501 already in use

**Solution:**
```bash
# Find process using port
lsof -i :5432
netstat -ano | findstr :5432  # Windows

# Kill process or change port in docker-compose.yml
```


#### Database Connection Errors

**Problem:** Cannot connect to database

**Solution:**
```bash
# Check if container is running
docker-compose ps

# Check logs
docker-compose logs timescaledb

# Verify connection
docker-compose exec timescaledb psql -U stockiq -d stockiq -c "SELECT 1"

# Check DATABASE_URL in .env
echo $DATABASE_URL
```

#### Celery Workers Not Processing Tasks

**Problem:** Tasks queued but not executing

**Solution:**
```bash
# Check worker status
docker-compose logs celery-worker

# Inspect active tasks
docker-compose exec celery-worker celery -A stockiq.infrastructure.tasks inspect active

# Restart workers
docker-compose restart celery-worker
```

#### High Memory Usage

**Problem:** Redis or PostgreSQL consuming too much memory

**Solution:**
```bash
# Check Redis memory
docker-compose exec redis redis-cli INFO memory

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHDB

# Check PostgreSQL connections
docker-compose exec timescaledb psql -U stockiq -d stockiq -c "SELECT count(*) FROM pg_stat_activity"

# Terminate idle connections
docker-compose exec timescaledb psql -U stockiq -d stockiq -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '5 minutes'"
```

#### API Rate Limit Errors

**Problem:** Too many requests to external APIs

**Solution:**
- Check `NEWSAPI_KEY`, `FINNHUB_API_KEY` are valid
- Reduce task frequency in Celery Beat schedule
- Upgrade API tier for higher limits

### Debug Mode

Enable debug logging:

```bash
# In .env
LOG_LEVEL=DEBUG

# Restart services
docker-compose restart
```

### Getting Help

- **Documentation:** https://github.com/yourusername/stockiq/wiki
- **Issues:** https://github.com/yourusername/stockiq/issues
- **Discussions:** https://github.com/yourusername/stockiq/discussions

---

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Redis Documentation](https://redis.io/documentation)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Streamlit Documentation](https://docs.streamlit.io/)

---

*For usage instructions, see the [User Guide](user-guide.md). For development, see the [Developer Guide](developer-guide.md).*
