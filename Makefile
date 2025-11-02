.PHONY: help install setup dev test lint clean docker-up docker-down migrate

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r backend/requirements.txt

setup: ## Setup environment and generate encryption key
	cp .env.example .env
	@echo "Generating encryption key..."
	@python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())" >> .env
	@echo "Environment file created. Please update JWT_SECRET in .env"

dev: ## Run development server
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests with coverage
	pytest backend/tests/ -v --cov=backend --cov-report=html --cov-report=term

test-fast: ## Run tests without coverage
	pytest backend/tests/ -v --maxfail=1 --disable-warnings -q

lint: ## Run pylint on backend code
	pylint backend/ --disable=C0114,C0116

format: ## Format code with black
	black backend/

docker-up: ## Start Docker containers
	docker-compose up -d

docker-down: ## Stop Docker containers
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-rebuild: ## Rebuild and restart Docker containers
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

migrate-create: ## Create a new Alembic migration
	@read -p "Enter migration message: " msg; \
	cd backend && alembic revision --autogenerate -m "$$msg"

migrate-up: ## Run database migrations
	cd backend && alembic upgrade head

migrate-down: ## Rollback last migration
	cd backend && alembic downgrade -1

clean: ## Clean up cache and temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete

db-shell: ## Connect to PostgreSQL database
	docker-compose exec postgres psql -U antika -d antika_auction

redis-cli: ## Connect to Redis CLI
	docker-compose exec redis redis-cli

init-db: ## Initialize database tables
	python -c "from backend.db.database import create_db_and_tables; create_db_and_tables()"
