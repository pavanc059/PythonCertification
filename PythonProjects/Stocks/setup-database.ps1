#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Automated setup script for PostgreSQL + TimescaleDB with Docker

.DESCRIPTION
    This script automates the setup of PostgreSQL 14+ with TimescaleDB extension
    using Docker containers. It performs the following steps:
    1. Checks Docker installation and status
    2. Creates .env file if it doesn't exist
    3. Starts PostgreSQL and Redis containers
    4. Waits for services to be healthy
    5. Initializes database schema and TimescaleDB
    6. Verifies installation

.EXAMPLE
    .\setup-database.ps1
    
.EXAMPLE
    .\setup-database.ps1 -SkipEnvCheck
#>

param(
    [switch]$SkipEnvCheck,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host "✅ $args" -ForegroundColor Green }
function Write-Info { Write-Host "ℹ️  $args" -ForegroundColor Cyan }
function Write-Warning { Write-Host "⚠️  $args" -ForegroundColor Yellow }
function Write-Error { Write-Host "❌ $args" -ForegroundColor Red }
function Write-Step { Write-Host "`n🔹 $args" -ForegroundColor Blue }

# Banner
Write-Host @"

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   StockIQ Database Setup                                  ║
║   PostgreSQL 14+ with TimescaleDB Extension               ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

# Step 1: Check Docker installation
Write-Step "Checking Docker installation..."

try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed"
    }
    Write-Success "Docker is installed: $dockerVersion"
} catch {
    Write-Error "Docker is not installed or not in PATH"
    Write-Info "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/"
    exit 1
}

# Step 2: Check if Docker is running
Write-Step "Checking if Docker is running..."

try {
    $dockerPs = docker ps 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker is not running"
    }
    Write-Success "Docker is running"
} catch {
    Write-Error "Docker Desktop is not running"
    Write-Info "Please start Docker Desktop and wait for it to fully initialize"
    Write-Info "Then run this script again"
    exit 1
}

# Step 3: Check docker-compose
Write-Step "Checking docker-compose..."

try {
    $composeVersion = docker-compose --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "docker-compose command failed"
    }
    Write-Success "docker-compose is available: $composeVersion"
} catch {
    Write-Error "docker-compose is not available"
    Write-Info "Please ensure Docker Desktop is properly installed"
    exit 1
}

# Step 4: Check .env file
if (-not $SkipEnvCheck) {
    Write-Step "Checking environment configuration..."
    
    if (-not (Test-Path ".env")) {
        Write-Warning ".env file not found"
        Write-Info "Creating .env file from .env.example..."
        
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-Success ".env file created"
            Write-Warning "IMPORTANT: Please edit .env file and set your configuration:"
            Write-Info "  - Set POSTGRES_PASSWORD to a secure password"
            Write-Info "  - Add API keys (optional for Phase 0.1)"
            Write-Info ""
            Write-Info "Press Enter to continue after editing .env, or Ctrl+C to exit..."
            Read-Host
        } else {
            Write-Error ".env.example file not found"
            exit 1
        }
    } else {
        Write-Success ".env file exists"
    }
}

# Step 5: Stop any existing containers
Write-Step "Stopping any existing containers..."

try {
    docker-compose down 2>&1 | Out-Null
    Write-Success "Existing containers stopped"
} catch {
    Write-Info "No existing containers to stop"
}

# Step 6: Start PostgreSQL and Redis
Write-Step "Starting PostgreSQL with TimescaleDB and Redis..."

try {
    Write-Info "Pulling latest images..."
    docker-compose pull timescaledb redis
    
    Write-Info "Starting containers..."
    docker-compose up -d timescaledb redis
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to start containers"
    }
    
    Write-Success "Containers started"
} catch {
    Write-Error "Failed to start containers: $_"
    Write-Info "Check logs with: docker-compose logs timescaledb redis"
    exit 1
}

# Step 7: Wait for services to be healthy
Write-Step "Waiting for services to be healthy..."

$maxWaitSeconds = 60
$waitInterval = 2
$elapsed = 0

Write-Info "Waiting for PostgreSQL to be ready (max ${maxWaitSeconds}s)..."

while ($elapsed -lt $maxWaitSeconds) {
    try {
        $health = docker inspect --format='{{.State.Health.Status}}' stockiq-timescaledb 2>&1
        
        if ($health -eq "healthy") {
            Write-Success "PostgreSQL is healthy"
            break
        }
        
        Write-Host "." -NoNewline
        Start-Sleep -Seconds $waitInterval
        $elapsed += $waitInterval
    } catch {
        Write-Host "." -NoNewline
        Start-Sleep -Seconds $waitInterval
        $elapsed += $waitInterval
    }
}

Write-Host ""  # New line after dots

if ($elapsed -ge $maxWaitSeconds) {
    Write-Error "PostgreSQL did not become healthy within ${maxWaitSeconds} seconds"
    Write-Info "Check logs with: docker-compose logs timescaledb"
    exit 1
}

# Check Redis
Write-Info "Checking Redis..."
try {
    $redisHealth = docker inspect --format='{{.State.Health.Status}}' stockiq-redis 2>&1
    if ($redisHealth -eq "healthy") {
        Write-Success "Redis is healthy"
    } else {
        Write-Warning "Redis health status: $redisHealth"
    }
} catch {
    Write-Warning "Could not check Redis health, but continuing..."
}

# Step 8: Verify Python environment
Write-Step "Checking Python environment..."

if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Success "Virtual environment found"
    Write-Info "Activating virtual environment..."
    & .\.venv\Scripts\Activate.ps1
} else {
    Write-Warning "Virtual environment not found at .venv"
    Write-Info "Using system Python..."
}

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python is available: $pythonVersion"
} catch {
    Write-Error "Python is not available"
    Write-Info "Please install Python 3.8+ or activate your virtual environment"
    exit 1
}

# Step 9: Initialize database
Write-Step "Initializing database schema and TimescaleDB..."

try {
    Write-Info "Running database initialization script..."
    python scripts\init_db.py
    
    if ($LASTEXITCODE -ne 0) {
        throw "Database initialization failed"
    }
    
    Write-Success "Database initialized successfully"
} catch {
    Write-Error "Database initialization failed: $_"
    Write-Info "Check the error messages above for details"
    exit 1
}

# Step 10: Verify installation
Write-Step "Verifying installation..."

Write-Info "Checking database tables..."
try {
    $tables = docker exec stockiq-timescaledb psql -U stockiq -d stockiq -c "\dt" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Database tables created successfully"
        if ($Verbose) {
            Write-Host $tables
        }
    }
} catch {
    Write-Warning "Could not verify tables, but database may still be working"
}

Write-Info "Checking TimescaleDB extension..."
try {
    $extension = docker exec stockiq-timescaledb psql -U stockiq -d stockiq -c "SELECT * FROM pg_extension WHERE extname = 'timescaledb';" 2>&1
    if ($LASTEXITCODE -eq 0 -and $extension -match "timescaledb") {
        Write-Success "TimescaleDB extension is installed"
        if ($Verbose) {
            Write-Host $extension
        }
    }
} catch {
    Write-Warning "Could not verify TimescaleDB extension"
}

Write-Info "Checking hypertables..."
try {
    $hypertables = docker exec stockiq-timescaledb psql -U stockiq -d stockiq -c "SELECT * FROM timescaledb_information.hypertables;" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Hypertables configured"
        if ($Verbose) {
            Write-Host $hypertables
        }
    }
} catch {
    Write-Warning "Could not verify hypertables"
}

# Step 11: Test Redis connection
Write-Info "Testing Redis connection..."
try {
    $redisPing = docker exec stockiq-redis redis-cli PING 2>&1
    if ($redisPing -match "PONG") {
        Write-Success "Redis is responding"
    }
} catch {
    Write-Warning "Could not verify Redis connection"
}

# Final summary
Write-Host @"

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ✅ Setup Complete!                                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

"@ -ForegroundColor Green

Write-Host "Database Connection Details:" -ForegroundColor Cyan
Write-Host "  Host:     localhost"
Write-Host "  Port:     5432"
Write-Host "  Database: stockiq"
Write-Host "  User:     stockiq"
Write-Host "  Password: (from .env file)"
Write-Host ""

Write-Host "Redis Connection Details:" -ForegroundColor Cyan
Write-Host "  Host: localhost"
Write-Host "  Port: 6379"
Write-Host ""

Write-Host "Container Status:" -ForegroundColor Cyan
docker-compose ps

Write-Host "`nUseful Commands:" -ForegroundColor Cyan
Write-Host "  View logs:           docker-compose logs -f timescaledb"
Write-Host "  Stop containers:     docker-compose down"
Write-Host "  Restart containers:  docker-compose restart"
Write-Host "  Connect to DB:       docker exec -it stockiq-timescaledb psql -U stockiq -d stockiq"
Write-Host "  Connect to Redis:    docker exec -it stockiq-redis redis-cli"
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. ✅ Phase 0.1.1 Complete - PostgreSQL + TimescaleDB configured"
Write-Host "  2. ➡️  Phase 0.1.2 - Redis Cache Setup (already running, needs configuration)"
Write-Host "  3. ➡️  Phase 0.1.3 - Celery Task Queue Setup"
Write-Host ""

Write-Success "Setup completed successfully!"
