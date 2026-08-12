# Docker Deployment Guide

## Overview

This guide covers deploying the StockIQ application using Docker Compose for local development and production environments, plus GitHub Container Registry for CI/CD.

## Architecture

The application consists of 6 Docker containers:

1. **timescaledb** - PostgreSQL 14 with TimescaleDB extension
2. **redis** - Redis 7 for caching and message broker
3. **celery-worker** - Background task processing
4. **celery-beat** - Task scheduler
5. **web** - Streamlit web application
6. **db-init** - One-time database initialization

## Quick Start

### 1. Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0+
- Git

### 2. Clone Repository

```bash
git clone https://github.com/yourusername/stockiq.git
cd stockiq
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.docker .env

# Edit .env with your API keys
notepad .env  # Windows
# nano .env   # Linux/Mac
```

**Required API Keys:**
- `NEWSAPI_KEY` - Get from https://newsapi.org/
- `FINNHUB_API_KEY` - Get from https://finnhub.io/
- `ALPHAVANTAGE_API_KEY` - Get from https://www.alphavantage.co/

### 4. Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 5. Initialize Database

The database is automatically initialized on first run by the `db-init` service.

To manually initialize:
```bash
docker-compose run --rm db-init
```

### 6. Access Application

- **Web Interface**: http://localhost:8501
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Docker Commands

### Service Management

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart web

# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f web

# Check service status
docker-compose ps

# Execute command in running container
docker-compose exec web bash
```

### Database Management

```bash
# Access PostgreSQL
docker-compose exec timescaledb psql -U stockiq -d stockiq

# Backup database
docker-compose exec timescaledb pg_dump -U stockiq stockiq > backup.sql

# Restore database
docker-compose exec -T timescaledb psql -U stockiq stockiq < backup.sql

# Check database status
docker-compose exec web python scripts/manage_db.py status
```

### Cache Management

```bash
# Access Redis CLI
docker-compose exec redis redis-cli

# Flush all cache
docker-compose exec redis redis-cli FLUSHALL

# Monitor Redis
docker-compose exec redis redis-cli MONITOR
```

### Celery Management

```bash
# View Celery worker status
docker-compose exec celery-worker celery -A stockiq.infrastructure.tasks inspect active

# View scheduled tasks
docker-compose exec celery-beat celery -A stockiq.infrastructure.tasks inspect scheduled

# Purge all tasks
docker-compose exec celery-worker celery -A stockiq.infrastructure.tasks purge
```

## Production Deployment

### 1. Security Hardening

Update `.env` file:
```env
# Use strong passwords
POSTGRES_PASSWORD=<strong-random-password>
SECRET_KEY=<strong-random-secret>
JWT_SECRET_KEY=<strong-random-jwt-secret>

# Disable debug mode
DEBUG=False
APP_ENV=production
LOG_LEVEL=WARNING
```

### 2. Resource Limits

Add resource limits to `docker-compose.yml`:

```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 3. Persistent Volumes

Volumes are automatically created:
- `timescaledb_data` - Database data
- `redis_data` - Redis persistence

Backup volumes:
```bash
# Backup database volume
docker run --rm -v stockiq_timescaledb_data:/data -v $(pwd):/backup ubuntu tar czf /backup/db-backup.tar.gz /data

# Restore database volume
docker run --rm -v stockiq_timescaledb_data:/data -v $(pwd):/backup ubuntu tar xzf /backup/db-backup.tar.gz -C /
```

### 4. Reverse Proxy (Nginx)

Add Nginx service to `docker-compose.yml`:

```yaml
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web
    networks:
      - stockiq-network
```

### 5. SSL/TLS Configuration

Use Let's Encrypt with Certbot:

```bash
# Install Certbot
docker run -it --rm --name certbot \
  -v "/etc/letsencrypt:/etc/letsencrypt" \
  -v "/var/lib/letsencrypt:/var/lib/letsencrypt" \
  certbot/certbot certonly --standalone \
  -d yourdomain.com
```

## GitHub Container Registry

### 1. Build and Push Image

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Build image
docker build -t ghcr.io/username/stockiq:latest .

# Push image
docker push ghcr.io/username/stockiq:latest
```

### 2. Pull and Run

```bash
# Pull image
docker pull ghcr.io/username/stockiq:latest

# Update docker-compose.yml to use registry image
services:
  web:
    image: ghcr.io/username/stockiq:latest
    # Remove 'build' section
```

### 3. GitHub Actions CI/CD

The `.github/workflows/ci-cd.yml` file automatically:
1. Runs tests on push/PR
2. Builds Docker image on main branch
3. Pushes to GitHub Container Registry
4. Deploys to production (configure deployment step)

**Setup:**
1. Enable GitHub Actions in repository settings
2. Add secrets in repository settings:
   - `NEWSAPI_KEY`
   - `FINNHUB_API_KEY`
   - `ALPHAVANTAGE_API_KEY`
3. Push to main branch to trigger workflow

## Cloud Deployment

### AWS ECS/Fargate

1. Push image to Amazon ECR
2. Create ECS task definition
3. Create ECS service
4. Configure Application Load Balancer

### Azure Container Instances

```bash
az container create \
  --resource-group stockiq-rg \
  --name stockiq-web \
  --image ghcr.io/username/stockiq:latest \
  --dns-name-label stockiq \
  --ports 8501
```

### Google Cloud Run

```bash
gcloud run deploy stockiq \
  --image ghcr.io/username/stockiq:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### DigitalOcean App Platform

1. Connect GitHub repository
2. Configure environment variables
3. Deploy from Docker Hub or GitHub Container Registry

## Monitoring

### Health Checks

```bash
# Check all services
docker-compose ps

# Check web application
curl http://localhost:8501/_stcore/health

# Check database
docker-compose exec timescaledb pg_isready -U stockiq

# Check Redis
docker-compose exec redis redis-cli ping
```

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f web
docker-compose logs -f celery-worker

# Export logs
docker-compose logs > logs.txt
```

### Metrics

Add Prometheus and Grafana:

```yaml
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs <service-name>

# Check container status
docker-compose ps

# Restart service
docker-compose restart <service-name>
```

### Database Connection Issues

```bash
# Check if database is ready
docker-compose exec timescaledb pg_isready -U stockiq

# Check database logs
docker-compose logs timescaledb

# Verify connection from web container
docker-compose exec web python -c "from stockiq.infrastructure.database import get_engine; get_engine().connect()"
```

### Redis Connection Issues

```bash
# Check Redis status
docker-compose exec redis redis-cli ping

# Check Redis logs
docker-compose logs redis

# Test connection
docker-compose exec web python -c "from stockiq.infrastructure.cache import get_redis_client; get_redis_client().ping()"
```

### Celery Tasks Not Running

```bash
# Check worker status
docker-compose logs celery-worker

# Check beat scheduler
docker-compose logs celery-beat

# Inspect active tasks
docker-compose exec celery-worker celery -A stockiq.infrastructure.tasks inspect active
```

### Out of Memory

```bash
# Check container memory usage
docker stats

# Increase memory limits in docker-compose.yml
# Or increase Docker Desktop memory allocation
```

## Scaling

### Horizontal Scaling

```bash
# Scale web service to 3 instances
docker-compose up -d --scale web=3

# Scale celery workers to 5 instances
docker-compose up -d --scale celery-worker=5
```

### Load Balancing

Add Nginx load balancer:

```yaml
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf
    depends_on:
      - web
```

## Backup and Recovery

### Automated Backups

Create backup script:

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"

# Backup database
docker-compose exec -T timescaledb pg_dump -U stockiq stockiq > $BACKUP_DIR/db_$DATE.sql

# Backup Redis
docker-compose exec redis redis-cli SAVE
docker cp stockiq-redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

echo "Backup completed: $DATE"
```

### Restore from Backup

```bash
# Restore database
docker-compose exec -T timescaledb psql -U stockiq stockiq < backups/db_20240101_120000.sql

# Restore Redis
docker cp backups/redis_20240101_120000.rdb stockiq-redis:/data/dump.rdb
docker-compose restart redis
```

## Performance Tuning

### PostgreSQL

Edit `docker-compose.yml`:

```yaml
  timescaledb:
    command: postgres -c shared_buffers=256MB -c max_connections=200
```

### Redis

```yaml
  redis:
    command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
```

### Celery

```yaml
  celery-worker:
    command: celery -A stockiq.infrastructure.tasks worker --loglevel=info --concurrency=8 --max-tasks-per-child=1000
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/stockiq/issues
- Documentation: https://github.com/yourusername/stockiq/wiki
- Email: support@stockiq.com
