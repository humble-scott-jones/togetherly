#!/usr/bin/env bash
# Interactive helper to set Stripe keys into .env safely (local only)
# Usage: ./scripts/stripe_setup.sh --write

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

print_help() {
  cat <<'EOF'
Usage: stripe_setup.sh [--write]

This script prompts for Stripe keys and writes them to the local .env file.
By default it prints the values it would write. Use --write to actually update .env.

EOF
}

WRITE=0
if [[ "${1-}" == "--write" ]]; then
  WRITE=1
fi

read -p "Publishable key (pk_test...): " PK
read -p "Secret key (sk_test...): " SK
read -p "Price ID (price_...): " PRICE
read -p "Product ID (prod_...): " PROD
read -p "Webhook secret (whsec_...) [optional]: " WHSEC

cat <<EOF
Will ${WRITE:+actually }write to $ENV_FILE with these values:
  STRIPE_PUBLISHABLE_KEY=$PK
  STRIPE_SECRET_KEY=$SK
  STRIPE_TEST_PRICE_ID=$PRICE
  STRIPE_PRODUCT_ID=$PROD
  STRIPE_WEBHOOK_SECRET=$WHSEC
EOF

if [[ $WRITE -eq 1 ]]; then
  # ensure .env exists
  touch "$ENV_FILE"
  # use awk to replace or append keys
  set_or_replace() {
    local key="$1"; local val="$2"; local file="$3"
    if grep -q "^${key}=" "$file"; then
      # replace existing line
      sed -i.bak "s|^${key}=.*$|${key}=${val}|" "$file"
    else
      echo "${key}=${val}" >> "$file"
    fi
  }
  set_or_replace STRIPE_PUBLISHABLE_KEY "$PK" "$ENV_FILE"
  set_or_replace STRIPE_SECRET_KEY "$SK" "$ENV_FILE"
  set_or_replace STRIPE_TEST_PRICE_ID "$PRICE" "$ENV_FILE"
  set_or_replace STRIPE_PRODUCT_ID "$PROD" "$ENV_FILE"
  set_or_replace STRIPE_WEBHOOK_SECRET "$WHSEC" "$ENV_FILE"
  echo "Updated $ENV_FILE (backup at ${ENV_FILE}.bak)"
else
  echo "Run with --write to update $ENV_FILE"
fi
