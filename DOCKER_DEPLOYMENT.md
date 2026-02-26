# Docker Deployment Guide for Autobus

This guide explains how to deploy the Autobus application using Docker and Docker Compose.

## Prerequisites

- **Docker**: [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose**: [Install Docker Compose](https://docs.docker.com/compose/install/)
- **Git**: For cloning the repository

## Project Structure

The Docker setup includes:
- **PostgreSQL 15**: Database server on port 5432
- **Redis 7**: Cache/session store on port 6379
- **Uvicorn Backend**: FastAPI application on port 8000

## Quick Start

### 1. Clone and Navigate to Project

```bash
git clone <repository-url>
cd autobus
```

### 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` to customize settings for your environment. Key variables:

```env
# Database credentials
POSTGRES_USER=autobusadmin
POSTGRES_PASSWORD=autobus098
PGDATABASE=autobus

# Redis settings
REDIS_PASSWORD=autobus098

# JWT Secret (change in production!)
SECRET_KEY=green-secret-keeps-gamma

# Debug mode (set to 'false' for production)
DEBUG=false

# Auto-run migrations
AUTO_MIGRATE=true
```

### 3. Build and Start Services

```bash
# Build the Docker image
docker-compose build

# Start all services (PostgreSQL, Redis, Backend)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

### 4. Verify Deployment

Check if services are healthy:

```bash
# List running containers
docker-compose ps

# Test the backend
curl http://localhost:8000/health

# Connect to PostgreSQL
# (from another terminal) docker exec -it autobus_db psql -U autobusadmin -d autobus

# Test Redis
docker exec autobus_redis redis-cli -a autobus098 ping
```

## Environment Configuration

### Database URLs

The application supports both traditional and Docker Postgres environment variables:

**Docker/Postgres standard vars (recommended):**
```env
PGHOST=db
PGPORT=5432
PGUSER=autobusadmin
PGPASSWORD=autobus098
PGDATABASE=autobus
```

**Alternative format:**
```env
SQLALCHEMY_DATABASE_URL=postgresql+asyncpg://autobusadmin:autobus098@db:5432/autobus
```

### Redis Configuration

```env
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=autobus098
```

### Security Configuration

```env
SECRET_KEY=your-super-secret-key      # Change this in production!
ALGORITHM=HS256
KID=autobus-kid
```

### Application Settings

```env
DEBUG=false                 # Production: false, Development: true
DB_ECHO=false              # Log SQL queries: false (disabled) or true (enabled)
LOG_LEVEL=INFO             # DEBUG, INFO, WARNING, ERROR
AUTO_MIGRATE=true          # Auto-apply Alembic migrations on startup
OTP_EXPIRE_MINUTES=5       # One-time password expiration
```

## Docker Compose Services

### PostgreSQL Service

- **Image**: postgres:15-alpine
- **Container Name**: autobus_db
- **Port**: 5432
- **Health Check**: Enabled
- **Volume**: `postgres_data:/var/lib/postgresql/data`

### Redis Service

- **Image**: redis:7-alpine
- **Container Name**: autobus_redis
- **Port**: 6379
- **Health Check**: Enabled
- **Volume**: `redis_data:/data`
- **Persistence**: AOF (Append-Only File) enabled

### Backend Service

- **Build Context**: Current directory (Dockerfile)
- **Container Name**: autobus_backend
- **Port**: 8000
- **Command**: Runs `startup.sh` which:
  1. Waits for PostgreSQL to be ready
  2. Waits for Redis to be ready
  3. Runs Alembic migrations (if AUTO_MIGRATE=true)
  4. Starts Gunicorn with Uvicorn workers

## Alembic Database Migrations

The startup script automatically handles database migrations:

```bash
# When AUTO_MIGRATE=true (default):
# 1. Creates initial migration if none exist
# 2. Detects model changes and creates new migrations
# 3. Applies all pending migrations
# 4. Starts the application

# Manual migration commands (inside container):
docker exec autobus_backend alembic current
docker exec autobus_backend alembic history
docker exec autobus_backend alembic downgrade -1
```

## Common Commands

```bash
# View logs in real-time
docker-compose logs -f

# View logs for specific service
docker-compose logs -f backend

# Execute command in running container
docker exec autobus_backend bash -c "python -c 'from src.config import settings; print(settings.DB_HOST)'"

# Access PostgreSQL shell
docker exec -it autobus_db psql -U autobusadmin -d autobus

# Access Redis CLI
docker exec -it autobus_redis redis-cli -a autobus098

# Rebuild images (if code changed)
docker-compose build --no-cache

# Remove everything (containers, volumes, networks)
docker-compose down -v

# View resource usage
docker stats
```

## Production Deployment Checklist

- [ ] Change `DEBUG=false`
- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Configure `BASE_FRONTEND_URL` correctly
- [ ] Set up proper logging (MongoDB optional)
- [ ] Configure RabbitMQ if using message queues
- [ ] Set appropriate `LOG_LEVEL` (INFO or WARNING)
- [ ] Configure proper database backups for `postgres_data` volume
- [ ] Configure proper backups for `redis_data` volume
- [ ] Test all authentication endpoints
- [ ] Verify database migrations completed successfully
- [ ] Setup resource limits in docker-compose.yml:
  ```yaml
  services:
    backend:
      deploy:
        resources:
          limits:
            cpus: '2'
            memory: 2G
  ```

## Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# - PostgreSQL not ready: Wait longer or check DB is running
# - Redis not ready: Check Redis service health
# - Migration errors: Review alembic logs
```

### Database connection errors

```bash
# Test database connection from backend
docker exec autobus_backend python -c "
import os
from sqlalchemy import create_engine
from src.config import settings
print(f'Connecting to: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_DATABASE}')
create_engine(settings.DB_URL_STRING).connect()
print('✓ Connection successful')
"
```

### Redis connection errors

```bash
# Check Redis
docker exec autobus_redis redis-cli -a autobus098 ping

# From backend container
docker exec autobus_backend redis-cli -h redis -a autobus098 ping
```

### Reset Everything

```bash
# Stop, remove containers, volumes, and rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

## Performance Tuning

### PostgreSQL Optimization

```yaml
services:
  db:
    environment:
      POSTGRES_INITDB_ARGS: "-c shared_buffers=256MB -c max_connections=200"
```

### Redis Optimization

```yaml
services:
  redis:
    command: >
      redis-server
      --requirepass autobus098
      --appendonly yes
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
```

### Backend Scaling

```yaml
# In docker-compose.yml, modify the backend command:
# gunicorn --workers 8 --worker-class uvicorn.workers.UvicornWorker
```

## Networking

All services communicate via the `autobus_network` bridge network:
- Backend ↔ PostgreSQL: `postgresql+asyncpg://db:5432/autobus`
- Backend ↔ Redis: `redis://redis:6379`

## Volumes

- **postgres_data**: Persistent PostgreSQL data
- **redis_data**: Persistent Redis data

Both are stored in Docker's default volume location. To locate them:
```bash
docker volume inspect autobus_postgres_data
docker volume inspect autobus_redis_data
```

## Next Steps

1. Deploy to your server/cloud platform
2. Configure reverse proxy (Nginx/Caddy) for HTTPS
3. Setup monitoring and logging
4. Configure automated backups
5. Setup CI/CD pipeline for automatic deployments

---

For issues or questions, check application logs: `docker-compose logs backend`
