# Togetherly (dev)
Run dev server:
```bash
source .venv/bin/activate
PORT=5001 python3 app.py
```
Run tests:
```bash
source .venv/bin/activate
PYTHONPATH=. pytest -q
# or run the helper script
./run_tests.sh
```
Run UI smoke tests (requires server running on port 5001). These are gated so they don't run by default during local development. Set the env var RUN_UI_SMOKE=1 to enable them.
```bash
# run unit tests only
PYTHONPATH=. pytest -q

# run UI smoke tests
RUN_UI_SMOKE=1 PYTHONPATH=. pytest -q
# Togetherly — development guide

This document explains how to set up and run Togetherly locally, run tests (including reproducing CI artifact collection), install optional Playwright tooling, and troubleshoot common issues.

## Prerequisites (macOS)

- Python 3.10+ (use pyenv if you need multiple versions)
- Git
- (Optional) Stripe CLI for sending webhook events locally

All commands below assume you run them from the repository root.

## 1) Create a reproducible virtual environment

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

Activate the venv when running commands interactively:

```bash
source .venv/bin/activate
```

## 2) Environment variables

Create a `.env` (or export these in your shell). Example minimal set:

```bash
FLASK_ENV=development
ALLOW_DEV_DEBUG=1
PORT=5001
STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_KEY
STRIPE_SECRET_KEY=sk_test_YOUR_KEY
STRIPE_PRICE_ID=price_test_YOUR_PRICE_ID
REELS_QUOTA_MONTHLY=5
```

Notes:
- `STRIPE_PRICE_ID` is the canonical price env var. Some code may still fall back to `STRIPE_TEST_PRICE_ID`.
- Keep real production secrets in your CI/host provider and out of version control.

Load `.env` into your shell (or use `direnv`) before running the server.

## 3) Install Playwright (optional but recommended for e2e)

Playwright is optional. Install and download browsers if you plan to run browser tests or capture screenshots.

```bash
.venv/bin/python -m pip install playwright
.venv/bin/python -m playwright install --with-deps
```

CI installs Playwright and browsers if Playwright tests are enabled.

## 4) Linting

Run `flake8` locally (CI runs a lint step):

```bash
.venv/bin/python -m pip install flake8
.venv/bin/python -m flake8
```

Fix any errors flagged by flake8. We keep flake8 non-blocking in CI by default; make it strict if you want it to fail builds.

## 5) Start the dev server

With the `.venv` active and env vars loaded, run:

```bash
PORT=5001 FLASK_ENV=development ALLOW_DEV_DEBUG=1 .venv/bin/python app.py
```

Sanity-check endpoint:

```bash
curl http://127.0.0.1:5001/__dev__/ping
# expected: a simple dev response (e.g. 'pong')
```

## 6) Useful dev endpoints

- `GET /__dev__/create_user` — dev helper to create a test user (dev mode only)
- `GET /api/current_user` — returns the current session user
- `POST /api/profile` — persist profile details used by the generator
- `POST /api/generate` — request content generation (reels will be gated to paid users)
- `GET /api/stripe-price` — returns authoritative Stripe price metadata for paywall copy

## 7) Running tests (pytest) — reproduce CI behavior

The CI collects a junit xml and captures logs. Replicate that locally:

```bash
# ensure test deps are installed
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install pytest

# run tests with junit output and capture console to a log file
.venv/bin/python -m pytest -q --maxfail=1 --junitxml=pytest-report.xml 2>&1 | tee pytest.log
```

After this runs you'll have `pytest-report.xml` and `pytest.log` at repo root (these are the same artifacts the CI uploads).

Notes:
- Unit tests mock Stripe where appropriate; integration tests that call Stripe require test keys.

## 8) Running Playwright tests (optional)

If you add Playwright tests, run them after installing Playwright and browsers:

```bash
# example: run playwright tests directory
.venv/bin/python -m pytest tests/playwright -q
```

Playwright typically writes artifacts under `playwright-report/`. The CI can be configured to upload that directory as artifacts.

## 9) Reproducing CI locally (summary)

CI performs these high-level steps:

1. Install Python deps
2. Install Playwright & browsers (optional)
3. Run flake8 (lint)
4. Run pytest with `--junitxml=pytest-report.xml` and capture stdout to `pytest.log`
5. Upload artifacts (junit xml, pytest log, Playwright artifacts)

To reproduce, run the commands in sections 1, 3, and 7 in sequence.

## 10) Troubleshooting

- Port already in use: `lsof -i :5001 -P -n` then `kill <pid>`
- Tests failing due to Stripe: ensure `STRIPE_SECRET_KEY` and `STRIPE_PUBLISHABLE_KEY` are set for integration tests or use the unit tests which mock Stripe
- Playwright missing deps: run `playwright install --with-deps` and follow Playwright error hints for system libraries

## 11) Notes & next steps

- Standardize documentation and `.env.example` to use `STRIPE_PRICE_ID` going forward.
- Consider enabling Playwright tests in CI if you want e2e coverage and artifact collection on failures.
- Tighten flake8 rules in CI and fix remaining lint issues.

If anything in these instructions doesn't work on your machine, paste the failing command and its output and I'll help fix it.
