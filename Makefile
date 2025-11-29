# Makefile for Orbit project

.PHONY: help install dev test format lint check clean run docker-up docker-down

help:  ## Show this help message
	@echo "Orbit - Task Orchestration System"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -e .

dev:  ## Install development dependencies
	pip install -e ".[dev]"

test:  ## Run tests
	pytest tests/ -v

format:  ## Format code with black and ruff
	black orbit/ tests/
	ruff check --fix orbit/ tests/

lint:  ## Run linters
	ruff check orbit/ tests/
	mypy orbit/ --ignore-missing-imports

check:  ## Run all quality checks
	./scripts/check.sh

clean:  ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -f orbit.db

run:  ## Run the development server
	uvicorn orbit.main:app --reload

docker-up:  ## Start Docker services
	docker-compose up -d

docker-down:  ## Stop Docker services
	docker-compose down
