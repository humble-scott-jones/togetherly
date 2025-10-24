#!/usr/bin/env bash
# Run the Playwright full acceptance test in headed (visible) mode.
# Usage: ./scripts/run_playwright_headed.sh

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Ensure deps and browsers are installed
python3 -m pip install -r requirements.txt
python3 -m playwright install --with-deps

# Run the specific test file in headed mode (HEADLESS=0)
HEADLESS=0 pytest tests/e2e/test_playwright_full.py -q
