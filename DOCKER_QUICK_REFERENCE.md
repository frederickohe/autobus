# Docker Quick Reference

A quick reference guide for common Docker operations with Autobus.

## Setup (First Time)

```bash
# Clone repository
git clone <repository-url>
cd autobus

# Copy environment file
cp .env.example .env

# Edit .env with your values
# nano .env  (or use your editor)

# Build and start
docker-compose build
docker-compose up -d

# Check status
docker-compose ps
```

## Start/Stop Services

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Stop and remove volumes (WARNING: deletes data!)
docker-compose down -v

# Restart services
docker-compose restart

# Restart specific service
docker-compose restart backend
```

## View Logs

```bash
# All services, follow mode
docker-compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f db
docker compose logs -f redis

# Last 50 lines
docker-compose logs --tail=50
```

## Connect to Services

```bash
# Backend bash shell
docker exec -it autobus_backend bash

# PostgreSQL shell
docker exec -it autobus_db psql -U autobusadmin -d autobus

# Redis CLI
docker exec -it autobus_redis redis-cli -a autobus098

# Run Python command
docker exec autobus_backend python -c "from src.config import settings; print(settings.DB_HOST)"
```

## Database Operations

```bash
# Backup database
docker exec autobus_db pg_dump -U autobusadmin autobus > backup.sql

# Restore database
docker exec -i autobus_db psql -U autobusadmin autobus < backup.sql

# Check migrations
docker exec autobus_backend alembic current
docker exec autobus_backend alembic history

# Manual migration
docker exec autobus_backend alembic downgrade -1
docker exec autobus_backend alembic upgrade +1
```

## Testing

```bash
# Test database connection
docker exec autobus_backend python -c \
  "from sqlalchemy import create_engine; from src.config import settings; \
  create_engine(settings.DB_URL_STRING).connect(); \
  print('✓ Database OK')"

# Test Redis connection
docker exec autobus_redis redis-cli -a autobus098 ping

# Test API
curl http://localhost:8000/health
curl -X GET http://localhost:8000/api/status
```

## Maintenance

```bash
# View resource usage
docker stats

# Remove unused resources
docker system prune -a

# Update images to latest version
docker-compose build --no-cache

# Check for service issues
docker-compose ps
docker-compose logs backend | tail -20
```

## Configuration Changes

```bash
# Edit environment
nano .env

# Rebuild and restart (for config changes)
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Or just restart without rebuilding
docker-compose restart backend
```

## Troubleshooting

```bash
# Check service status
docker-compose ps
docker-compose logs backend          # Check for errors

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d

# Check disk usage
docker system df

# Clean up (warning: removes unused containers)
docker system prune

# View specific error
docker-compose logs backend | grep ERROR
```

## Production Commands

```bash
# Deploy with safety checks
chmod +x deploy-production.sh
./deploy-production.sh

# Or use Makefile
make rebuild           # Clean rebuild
make status           # Check all services
make test-db          # Verify database
make test-redis       # Verify Redis
make db-backup        # Backup database
```

## Using Makefile (Recommended)

```bash
# Show all available commands
make help

# Build
make build

# Start
make up

# Stop
make down

# Logs
make logs
make logs-backend

# Check status
make status

# Shell access
make shell-backend
make shell-db
make shell-redis

# Testing
make test-db
make test-redis

# Migrations
make migrate-current
make migrate-history

# Maintenance
make clean            # WARNING: deletes data
make rebuild          # Clean rebuild
make db-backup        # Backup database
```

## Environment Variables Quick Edit

```bash
# Add or update a variable
# Edit .env file directly, then restart:
docker-compose restart backend

# Or rebuild if it's a database-related change:
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Common Issues & Solutions

**Port Already in Use**:
```bash
# Change port in docker-compose.yml or stop conflicting service
docker ps
docker stop <container-id>
```

**Container keeps restarting**:
```bash
# Check logs
docker-compose logs backend | tail -50

# May need to rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

**Database not initializing**:
```bash
# Wait longer and check logs
docker-compose logs db | tail -20

# May need to recreate database
docker-compose down -v
docker volume rm autobus_postgres_data
docker-compose up -d
```

**Out of disk space**:
```bash
# Clean up Docker resources
docker system prune -a
docker volume prune

# Check disk usage
docker system df
```

## Useful Docker Commands

```bash
# General
docker ps                          # List running containers
docker ps -a                       # List all containers
docker images                      # List images
docker volume ls                   # List volumes
docker network ls                  # List networks

# Info
docker inspect <container>         # Detailed container info
docker logs <container>            # Container logs
docker stats <container>           # Resource usage

# Network
docker network inspect autobus_network

# Volume
docker volume inspect autobus_postgres_data
docker volume rm <volume-name>    # Delete volume (WARNING!)

# Cleanup
docker rm <container>              # Remove container
docker rmi <image>                # Remove image
docker volume rm <volume>          # Remove volume
docker system prune               # Clean unused resources
```

## Documentation

- Full deployment guide: [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md)
- Changes summary: [DEPLOYMENT_CHANGES.md](./DEPLOYMENT_CHANGES.md)
- Environment template: [.env.example](./.env.example)

---

**Need help?** Run `docker-compose logs -f backend` to see what's happening in real-time.
