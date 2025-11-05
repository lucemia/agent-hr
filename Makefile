.PHONY: lint format check test install clean help pre-commit pre-commit-install pre-commit-update dump-db

# Default target
help:
	@echo "Available commands:"
	@echo "  lint              - Run ruff linter"
	@echo "  format            - Run ruff formatter"
	@echo "  check             - Run both linter and formatter (check only)"
	@echo "  fix               - Run linter with auto-fix and formatter"
	@echo "  pre-commit        - Run all pre-commit hooks"
	@echo "  pre-commit-install- Install pre-commit hooks"
	@echo "  pre-commit-update - Update pre-commit hooks"
	@echo "  install           - Install dependencies and pre-commit hooks"
	@echo "  clean             - Clean cache and temporary files"
	@echo "  test              - Run tests"
	@echo "  test-verbose      - Run tests with verbose output"
	@echo "  test-coverage     - Run tests with coverage report"
	@echo "  test-watch        - Run tests in watch mode"
	@echo "  dump-db           - Dump database to SQL file"

# Linting
lint:
	uv run ruff check .

# Formatting
format:
	uv run ruff format .

# Check both linting and formatting
check:
	uv run ruff check .
	uv run ruff format --check .

# Fix issues automatically
fix:
	uv run ruff check --fix .
	uv run ruff format .

# Pre-commit hooks
pre-commit:
	uv run pre-commit run --all-files

pre-commit-install:
	uv run pre-commit install

pre-commit-update:
	uv run pre-commit autoupdate

# Install dependencies
install:
	uv sync
	uv run pre-commit install

# Clean cache and temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .ruff_cache

# Testing
test:
	uv run pytest

test-verbose:
	uv run pytest -v

test-coverage:
	uv run pytest --cov=import_resume --cov-report=html --cov-report=term

test-watch:
	uv run pytest-watch

# Database dump
dump-db:
	sqlite3 resume.db .dump > resume.sql
