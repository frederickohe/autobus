.PHONY: help build up down logs restart clean test migrate

help:
	@echo "Autobus Docker Deployment - Available Commands"
	@echo ""
	@echo "  make build              Build Docker images"
	@echo "  make up                 Start all services in background"
	@echo "  make down               Stop all services"
	@echo "  make logs               View logs from all services (follow mode)"
	@echo "  make logs-backend       View backend logs only"
	@echo "  make restart            Restart all services"
	@echo "  make clean              Remove containers, volumes, and networks"
	@echo "  make status             Show status of all services"
	@echo "  make shell-backend      Open bash shell in backend container"
	@echo "  make shell-db           Open PostgreSQL shell"
	@echo "  make shell-redis        Open Redis CLI"
	@echo "  make test-db            Test database connection"
	@echo "  make test-redis         Test Redis connection"
	@echo "  make migrate-current    Show current migration status"
	@echo "  make migrate-history    Show migration history"
	@echo "  make rebuild            Clean rebuild all images and services"
	@echo ""

build:
	@echo "Building Docker images..."
	docker-compose build

up:
	@echo "Starting services..."
	docker-compose up -d
	@echo ""
	@echo "Services are starting. Run 'make status' to check status."

down:
	@echo "Stopping services..."
	docker-compose down

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-db:
	docker-compose logs -f db

logs-redis:
	docker-compose logs -f redis

restart:
	@echo "Restarting services..."
	docker-compose restart

clean:
	@echo "WARNING: This will remove all containers, volumes, and data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo "Cleanup complete"; \
	else \
		echo "Cleanup cancelled"; \
	fi

rebuild: clean build up
	@echo "Rebuild complete! Services are starting..."

status:
	@echo "Service Status:"
	@docker-compose ps
	@echo ""
	@echo "Health Checks:"
	@docker exec autobus_backend curl -s http://localhost:8000/health 2>/dev/null || echo "Backend: Starting..."
	@docker exec autobus_db pg_isready -U autobusadmin 2>/dev/null || echo "Database: Not ready"
	@docker exec autobus_redis redis-cli -a autobus098 ping 2>/dev/null || echo "Redis: Not ready"

shell-backend:
	docker exec -it autobus_backend bash

shell-db:
	docker exec -it autobus_db psql -U autobusadmin -d autobus

shell-redis:
	docker exec -it autobus_redis redis-cli -a autobus098

test-db:
	@echo "Testing PostgreSQL connection..."
	docker exec autobus_backend python -c \
		"from sqlalchemy import create_engine; from src.config import settings; \
		print(f'Connecting to: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_DATABASE}'); \
		create_engine(settings.DB_URL_STRING).connect(); \
		print('✓ Database connection successful')"

test-redis:
	@echo "Testing Redis connection..."
	docker exec autobus_redis redis-cli -a autobus098 ping
	@echo "✓ Redis connection successful"

migrate-current:
	@echo "Current migration status:"
	docker exec autobus_backend alembic current

migrate-history:
	@echo "Migration history:"
	docker exec autobus_backend alembic history --oneline

db-backup:
	@echo "Backing up PostgreSQL database..."
	@mkdir -p ./backups
	docker exec autobus_db pg_dump -U autobusadmin autobus > ./backups/autobus_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup complete: ./backups/"

ps:
	docker-compose ps

stats:
	docker stats autobus_backend autobus_db autobus_redis

pull-logs:
	docker-compose logs --timestamps --follow

init-dev:
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Created .env from .env.example"; \
	fi
	@echo "✓ Running 'make build && make up'"
	@$(MAKE) build
	@$(MAKE) up
	@echo ""
	@echo "Setup complete! Services should be starting."
	@echo "Run 'make status' to check if everything is ready."
	@echo "View logs with: make logs"
