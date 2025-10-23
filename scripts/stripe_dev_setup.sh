#!/usr/bin/env bash
# Helper to create a .env from .env.example and optionally run stripe listen
set -euo pipefail
TEMPLATE=.env.example
OUT=.env
if [ ! -f "$TEMPLATE" ]; then
  echo "Missing $TEMPLATE"
  exit 1
fi
if [ -f "$OUT" ]; then
  echo "$OUT already exists. Remove it first if you want to recreate."
  exit 1
fi
cp "$TEMPLATE" "$OUT"
cat <<EOF
Created .env from .env.example. Edit .env and fill in your Stripe test keys (STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_TEST_PRICE_ID).

If you have the Stripe CLI installed and want to forward webhooks to your local server, run:

  stripe listen --forward-to http://localhost:5001/api/stripe-webhook

When the listen command starts it will show a webhook signing secret (starts with whsec_...). Add that value to STRIPE_WEBHOOK_SECRET in .env.

To set .env values from the command line you can run (example):

  sed -i '' 's|sk_test_REPLACE_ME|sk_test_XXX|g' .env
  sed -i '' 's|pk_test_REPLACE_ME|pk_test_XXX|g' .env
  sed -i '' 's|price_REPLACE_ME|price_XXX|g' .env
  sed -i '' 's|whsec_REPLACE_ME|whsec_XXX|g' .env

EOF
chmod +x "$OUT" || true
echo "Done. Edit .env and run the server with: FLASK_APP=app.py FLASK_ENV=development FLASK_RUN_PORT=5001 flask run --host=127.0.0.1"
