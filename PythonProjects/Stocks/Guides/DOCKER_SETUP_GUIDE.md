# Docker Setup Guide for StockIQ

This guide will help you set up PostgreSQL 14+ with TimescaleDB extension using Docker.

## Prerequisites

1. **Docker Desktop** must be installed and running
   - Download from: https://www.docker.com/products/docker-desktop/
   - After installation, start Docker Desktop
   - Verify Docker is running: `docker --version`

## Quick Start

### Step 1: Start Docker Desktop

1. Open Docker Desktop application
2. Wait for Docker to fully start (whale icon in system tray should be steady)
3. Verify Docker is running:
   ```powershell
   docker --version
   docker ps
   ```

### Step 2: Create Environment File

Copy the example environment file and configure it:

```powershell
# Copy the example file
Copy-Item .env.example .env

# Edit .env file and set your configuration
# At minimum, set a secure POSTGRES_PASSWORD
```

**Important**: Update the following in your `.env` file:
- `POSTGRES_PASSWORD`: Set a secure password for PostgreSQL
- API keys (optional for Phase 0.1, but needed later):
  - `NEWSAPI_KEY`: Get from https://newsapi.org/
  - `FINNHUB_API_KEY`: Get from https://finnhub.io/
  - `ALPHAVANTAGE_API_KEY`: Get from https://www.alphavantage.co/

### Step 3: Start PostgreSQL and Redis

Start only the database and cache services:

```powershell
# Start PostgreSQL with TimescaleDB and Redis
docker-compose up -d timescaledb redis

# Check if containers are running
docker-compose ps

# View logs to ensure successful startup
docker-compose logs timescaledb
docker-compose logs redis
```

Expected output:
```
NAME                    STATUS              PORTS
stockiq-timescaledb     Up X seconds        0.0.0.0:5432->5432/tcp
stockiq-redis           Up X seconds        0.0.0.0:6379->6379/tcp
```

### Step 4: Initialize Database

Run the database initialization script:

```powershell
# Activate virtual environment (if not already activated)
.\.venv\Scripts\Activate.ps1

# Run database initialization
python scripts\init_db.py
```

Expected output:
```
✅ Database initialization completed successfully!

Next steps:
1. Verify tables: psql -d stockiq -c '\dt'
2. Check hypertables: psql -d stockiq -c 'SELECT * FROM timescaledb_information.hypertables;'
3. Start implementing Phase 0.1.2 - Redis Cache Setup
```

### Step 5: Verify Installation

Verify PostgreSQL and TimescaleDB are working:

```powershell
# Connect to PostgreSQL container
docker exec -it stockiq-timescaledb psql -U stockiq -d stockiq

# Inside psql, run these commands:
# List all tables
\dt

# Check TimescaleDB extension
SELECT * FROM pg_extension WHERE extname = 'timescaledb';

# Check hypertables
SELECT * FROM timescaledb_information.hypertables;

# Exit psql
\q
```

Verify Redis is working:

```powershell
# Connect to Redis container
docker exec -it stockiq-redis redis-cli

# Inside redis-cli, run:
PING
# Should return: PONG

# Exit redis-cli
exit
```

## Container Management

### Start All Services

```powershell
# Start all services (database, cache, workers, web)
docker-compose up -d

# View logs for all services
docker-compose logs -f
```

### Stop Services

```powershell
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v
```

### Restart Services

```powershell
# Restart specific service
docker-compose restart timescaledb
docker-compose restart redis

# Restart all services
docker-compose restart
```

### View Logs

```powershell
# View logs for specific service
docker-compose logs -f timescaledb
docker-compose logs -f redis
docker-compose logs -f celery-worker

# View logs for all services
docker-compose logs -f
```

## Database Connection Details

When containers are running, you can connect to PostgreSQL using:

- **Host**: `localhost` (from host machine) or `timescaledb` (from other containers)
- **Port**: `5432`
- **Database**: `stockiq`
- **User**: `stockiq`
- **Password**: Value from `POSTGRES_PASSWORD` in `.env` file

Connection string format:
```
postgresql://stockiq:your_password@localhost:5432/stockiq
```

## Redis Connection Details

- **Host**: `localhost` (from host machine) or `redis` (from other containers)
- **Port**: `6379`
- **Database**: `0` (default)

Connection string format:
```
redis://localhost:6379/0
```

## Troubleshooting

### Docker Desktop Not Running

**Error**: `error during connect: This error may indicate that the docker daemon is not running`

**Solution**:
1. Open Docker Desktop application
2. Wait for it to fully start
3. Check system tray for Docker whale icon
4. Try command again

### Port Already in Use

**Error**: `Bind for 0.0.0.0:5432 failed: port is already allocated`

**Solution**:
1. Check if PostgreSQL is already running locally:
   ```powershell
   Get-Process -Name postgres -ErrorAction SilentlyContinue
   ```
2. Either stop local PostgreSQL or change port in `docker-compose.yml`:
   ```yaml
   ports:
     - "5433:5432"  # Use port 5433 on host
   ```

### Container Fails to Start

**Error**: Container exits immediately or shows unhealthy status

**Solution**:
1. Check container logs:
   ```powershell
   docker-compose logs timescaledb
   ```
2. Verify environment variables in `.env` file
3. Remove volumes and restart:
   ```powershell
   docker-compose down -v
   docker-compose up -d timescaledb redis
   ```

### Database Connection Refused

**Error**: `psycopg2.OperationalError: could not connect to server`

**Solution**:
1. Verify container is running:
   ```powershell
   docker-compose ps
   ```
2. Check container health:
   ```powershell
   docker-compose logs timescaledb
   ```
3. Wait for database to fully initialize (can take 10-30 seconds)
4. Verify connection string in `.env` matches container configuration

### TimescaleDB Extension Not Found

**Error**: `extension "timescaledb" does not exist`

**Solution**:
1. Verify you're using the correct Docker image:
   ```yaml
   image: timescale/timescaledb:latest-pg14
   ```
2. Recreate container:
   ```powershell
   docker-compose down
   docker-compose up -d timescaledb
   ```
3. Run init script again:
   ```powershell
   python scripts\init_db.py
   ```

## Next Steps

After successful setup:

1. ✅ **Phase 0.1.1 Complete**: PostgreSQL 14+ with TimescaleDB is installed and configured
2. ➡️ **Phase 0.1.2**: Redis Cache Setup (already running, needs configuration)
3. ➡️ **Phase 0.1.3**: Celery Task Queue Setup

## Useful Commands

```powershell
# Check Docker version
docker --version
docker-compose --version

# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# View container resource usage
docker stats

# Execute command in container
docker exec -it stockiq-timescaledb bash

# View container details
docker inspect stockiq-timescaledb

# Remove all stopped containers
docker container prune

# Remove unused volumes
docker volume prune
```

## Production Considerations

For production deployment:

1. **Security**:
   - Use strong passwords (not default values)
   - Don't expose database ports publicly
   - Use Docker secrets for sensitive data
   - Enable SSL/TLS for database connections

2. **Performance**:
   - Increase shared_buffers in PostgreSQL config
   - Configure work_mem and maintenance_work_mem
   - Set up connection pooling with pgbouncer
   - Monitor resource usage and adjust limits

3. **Backup**:
   - Set up automated backups using pg_dump
   - Store backups in separate location
   - Test restore procedures regularly
   - Consider using TimescaleDB continuous aggregates

4. **Monitoring**:
   - Set up Prometheus + Grafana for metrics
   - Monitor database performance
   - Set up alerts for critical issues
   - Track query performance

## Resources

- Docker Documentation: https://docs.docker.com/
- PostgreSQL Documentation: https://www.postgresql.org/docs/14/
- TimescaleDB Documentation: https://docs.timescale.com/
- Docker Compose Documentation: https://docs.docker.com/compose/
