.PHONY: lint format check test install clean help

# Default target
help:
	@echo "Available commands:"
	@echo "  lint     - Run ruff linter"
	@echo "  format   - Run ruff formatter"
	@echo "  check    - Run both linter and formatter (check only)"
	@echo "  fix      - Run linter with auto-fix and formatter"
	@echo "  install  - Install dependencies"
	@echo "  clean    - Clean cache and temporary files"
	@echo "  test     - Run tests (placeholder)"

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

# Install dependencies
install:
	uv sync

# Clean cache and temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .ruff_cache

# Placeholder for tests
test:
	@echo "No tests configured yet"