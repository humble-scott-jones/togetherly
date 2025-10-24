Environment file guidance for local development

Quick start

1. Copy the example into a working `.env` file (do not commit `.env`):

   cp .env.example .env

   or use the provided `.env.dev` for quick testing:

   cp .env.dev .env

2. Load environment variables into your current shell (zsh):

   export $(cat .env | xargs)

   Now run the Flask app:

   python3 app.py

Notes and best practices

- Never commit a `.env` file with real secrets. The repo's `.gitignore` already includes `.env`.
- Use `.env.example` as the template for required keys. Fill in real Stripe test keys only for local testing.
- For more advanced workflows use direnv, dotenv, or a process manager (e.g., foreman or Honcho) that loads env files for you.
 - For Python runs, we now support `python-dotenv` which loads `.env` automatically when the app starts.
    Install with your environment's pip (it's included in `requirements.txt`):

    python3 -m pip install -r requirements.txt

    After that, simply running `python3 app.py` will load `.env` or `.env.dev` automatically.

E2E smoke tests

We include an end-to-end smoke runner at `scripts/e2e_run.sh`. It:

- Ensures `.env` exists (copies from `.env.dev` if needed)
- Starts the server with the environment loaded
- Runs basic flows (create dev user, save profile, generate posts) and verifies the response
- Restores the DB backup

Run it with:

```
./scripts/e2e_run.sh
```

Or via Makefile:

```
make e2e
```

Check `tmp/` for logs and request/response outputs after the run.
- The `REELS_QUOTA_MONTHLY` variable controls monthly reel generation quota in dev. Lower it for quick testing.
- If you need to run tests that require a clean DB, remove or move `togetherly.db` before starting the app.

Makefile and direnv

- A simple `Makefile` is included with targets:
   - `make dev` — copies `.env.dev` to `.env` (if not present) and starts the app with `python3 app.py`.
   - `make test` — runs `pytest -q` (install `pytest` in your virtualenv first).

- A `.envrc` is included for `direnv`. If you use `direnv`, run `direnv allow` in the repo root and it will load `.env.dev` automatically.
