# Simple helper Makefile for local development

.PHONY: dev test

# Start development server. Will copy .env.dev to .env if .env doesn't exist.
dev:
	@echo "Starting dev server (PORT from .env or default 5001)"
	@cp -n .env.dev .env || true
	@echo "Loading .env and launching server..."
	@export $(cat .env | xargs) && python3 app.py

# Run tests (requires pytest to be installed in your environment)
test:
	@echo "Running tests (pytest required)"
	pytest -q

e2e:
	@echo "Running end-to-end smoke test (will start server, run checks, then shut down)"
	@./scripts/e2e_run.sh

playwright-install:
	@echo "Installing Playwright browsers (required once)"
	@python3 -m pip install -r requirements.txt
	@python3 -m playwright install --with-deps

e2e-playwright:
	@echo "Run Playwright E2E tests (ensure playwright browsers are installed)"
	@python3 -m pytest tests/e2e -q
