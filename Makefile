.PHONY: help install run docker-build docker-run docker-stop test clean format lint backup

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Hajri.ai - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing dev dependencies...$(NC)"
	pip install -r requirements.txt -r requirements-dev.txt
	@echo "$(GREEN)✓ Dev dependencies installed$(NC)"

setup: install ## Setup database and environment
	@echo "$(GREEN)✓ Database setup handled automatically by app$(NC)"

run: ## Run the application with uv (fastest)
	@echo "$(BLUE)Starting Hajri.ai with uv...$(NC)"
	uv run streamlit run src/app.py

run-pip: ## Run the application with pip
	@echo "$(BLUE)Starting Hajri.ai...$(NC)"
	streamlit run src/app.py

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker-compose build
	@echo "$(GREEN)✓ Docker image built$(NC)"

docker-run: ## Run with Docker Compose
	@echo "$(BLUE)Starting Hajri.ai with Docker...$(NC)"
	docker-compose up

docker-run-bg: ## Run with Docker in background
	@echo "$(BLUE)Starting Hajri.ai in background...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Running at http://localhost:8501$(NC)"

docker-stop: ## Stop Docker containers
	@echo "$(BLUE)Stopping containers...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Containers stopped$(NC)"

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-clean: ## Remove Docker containers and images
	@echo "$(BLUE)Cleaning Docker resources...$(NC)"
	docker-compose down -v
	docker rmi hajri-ai_hajri-ai 2>/dev/null || true
	@echo "$(GREEN)✓ Docker cleaned$(NC)"

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	pytest tests/ -v
	@echo "$(GREEN)✓ Tests complete$(NC)"

test-cov: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest tests/ --cov=src --cov-report=html
	@echo "$(GREEN)✓ Coverage report generated$(NC)"

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	black .
	isort .
	@echo "$(GREEN)✓ Code formatted$(NC)"

lint: ## Lint code with flake8
	@echo "$(BLUE)Linting code...$(NC)"
	flake8 src/
	@echo "$(GREEN)✓ Linting complete$(NC)"

type-check: ## Type check with mypy
	@echo "$(BLUE)Type checking...$(NC)"
	mypy src/
	@echo "$(GREEN)✓ Type check complete$(NC)"

backup: ## Create backup of database and training images
	@echo "$(BLUE)Creating backup...$(NC)"
	python3 scripts/backup_data.py
	@echo "$(GREEN)✓ Backup complete$(NC)"

clean: ## Clean build artifacts and cache
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ htmlcov/ .coverage
	@echo "$(GREEN)✓ Cleaned$(NC)"

dev: install-dev setup ## Setup development environment
	@echo "$(GREEN)✓ Development environment ready$(NC)"
	@echo "$(YELLOW)Run 'make run' to start the application$(NC)"

prod: docker-build docker-run-bg ## Deploy to production with Docker
	@echo "$(GREEN)✓ Production deployment complete$(NC)"
	@echo "$(YELLOW)Application running at http://localhost:8501$(NC)"

all: clean install setup run ## Clean, install, setup, and run

check: format lint type-check test ## Run all checks (format, lint, type-check, test)
	@echo "$(GREEN)✓ All checks passed$(NC)"
