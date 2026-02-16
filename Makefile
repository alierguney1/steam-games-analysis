.PHONY: help setup up down logs clean test

help:
	@echo "Steam Games Analysis - Development Commands"
	@echo "==========================================="
	@echo "setup     - Initial setup (copy .env, create directories)"
	@echo "up        - Start all services with Docker Compose"
	@echo "down      - Stop all services"
	@echo "logs      - View logs from all services"
	@echo "clean     - Clean up Docker volumes and temporary files"
	@echo "test      - Run backend tests"
	@echo "validate  - Validate database schema"

setup:
	@echo "Setting up development environment..."
	cp -n configs/.env.example .env || true
	mkdir -p backend/logs
	@echo "✓ Setup complete!"

up:
	@echo "Starting services..."
	cd docker && docker compose up -d
	@echo "✓ Services started!"
	@echo "  - Frontend: http://localhost:5173"
	@echo "  - Backend API: http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/api/docs"
	@echo "  - PostgreSQL: localhost:5432"

down:
	@echo "Stopping services..."
	cd docker && docker compose down
	@echo "✓ Services stopped!"

logs:
	cd docker && docker compose logs -f

clean:
	@echo "Cleaning up..."
	cd docker && docker compose down -v
	rm -rf backend/logs/*
	@echo "✓ Cleanup complete!"

test:
	@echo "Running backend tests..."
	cd backend && poetry run pytest -v

validate:
	@echo "Validating database schema..."
	cd backend && poetry run python ../scripts/validate_schema.py
