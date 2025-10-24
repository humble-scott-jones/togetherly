#!/usr/bin/env bash
# Simple E2E smoke runner for local dev.
# - Ensures .env exists (copies from .env.dev if needed)
# - Backs up DB
# - Starts the server with env loaded
# - Runs a few API calls to confirm basic flows
# - Kills server and restores DB backup

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="$ROOT_DIR/.env"
LOG_DIR="$ROOT_DIR/tmp"
mkdir -p "$LOG_DIR"
SERVER_LOG="$LOG_DIR/server.log"
PID_FILE="$LOG_DIR/server.pid"
BACKUP_DB="$LOG_DIR/togetherly.db.bak"

if [ ! -f "$ENV_FILE" ]; then
  if [ -f .env.dev ]; then
    echo ".env not found — copying .env.dev -> .env"
    cp .env.dev .env
  else
    echo "No .env or .env.dev present. Create one from .env.example or .env.dev." >&2
    exit 1
  fi
fi

# Load env into this shell by sourcing and exporting variables (handles comments safely)
if [ -f "$ENV_FILE" ]; then
  # export all variables sourced from .env
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

# Backup DB if present
if [ -f togetherly.db ]; then
  echo "Backing up togetherly.db to $BACKUP_DB"
  mv togetherly.db "$BACKUP_DB" || true
fi

# Start server in background
echo "Starting server... (logs -> $SERVER_LOG)"
# Use python3 from PATH; if project venv exists prefer it
PY="$(which python3)"
if [ -x "./.venv/bin/python" ]; then
  PY="./.venv/bin/python"
fi
$PY app.py > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"

# Wait for server to start (timeout)
echo "Waiting for server to be ready..."
READY=0
for i in {1..30}; do
  if curl -s "http://127.0.0.1:${PORT:-5001}/__dev__/ping" | grep -q pong; then
    READY=1
    break
  fi
  sleep 1
done
if [ "$READY" -ne 1 ]; then
  echo "Server failed to start within timeout. Check $SERVER_LOG" >&2
  cat "$SERVER_LOG" | sed -n '1,200p'
  kill $SERVER_PID || true
  exit 2
fi

# Run E2E calls: create dev user, save a profile with reel_style, request generation for short_video
set -x
curl -s -c cookies.txt -X POST -H "Content-Type: application/json" -d '{"email":"e2e+dev@example.com","is_paid":true}' "http://127.0.0.1:${PORT:-5001}/__dev__/create_user" > "$LOG_DIR/create_user.json" || true
sleep 0.5
# Save a profile with details
curl -s -b cookies.txt -X POST -H "Content-Type: application/json" \
  -d '{"industry":"Realtor","tone":"friendly","platforms":["short_video"],"brand_keywords":["listings"],"niche_keywords":[],"goals":["New listings"],"company":"TestCo","details":{"reel_style":"Property b-roll + captions","reel_length":30},"include_images":false}' \
  "http://127.0.0.1:${PORT:-5001}/api/profile" > "$LOG_DIR/save_profile.json" || true
sleep 0.5
# Request generation (3 days sample)
curl -s -b cookies.txt -X POST -H "Content-Type: application/json" -d '{"platforms":["short_video"],"days":3}' "http://127.0.0.1:${PORT:-5001}/api/generate" > "$LOG_DIR/generate.json" || true

set +x

# Basic assertions
if grep -q "\"posts\"" "$LOG_DIR/generate.json"; then
  echo "E2E: generate returned posts — basic success"
else
  echo "E2E: generate did not return posts, see $LOG_DIR/generate.json" >&2
  tail -n 200 "$SERVER_LOG"
  kill $SERVER_PID || true
  exit 3
fi

# Stronger validation: ensure generated posts include reel objects with required keys
python3 - <<'PY'
import json,sys
f='tmp/generate.json'
try:
    data=json.load(open(f))
except Exception as e:
    print('Could not parse',f,e,file=sys.stderr); sys.exit(4)
posts=data.get('posts') or []
if not posts:
    print('No posts in generate.json',file=sys.stderr); sys.exit(5)
missing=False
for p in posts:
    reel=p.get('reel')
    if not reel:
        print('Post missing reel object',p,file=sys.stderr); missing=True; break
    for k in ('ranked_hooks','beats','shot_list','srt','thumbnail_prompt'):
        if k not in reel:
            print(f"Reel missing key: {k}",file=sys.stderr); missing=True; break
    if missing:
        break
if missing:
    sys.exit(6)
print('E2E: detailed reel validation passed')
PY

# Cleanup: stop server
echo "Stopping server (pid $SERVER_PID)"
kill $SERVER_PID || true
rm -f "$PID_FILE"

# Restore DB backup if existed
if [ -f "$BACKUP_DB" ]; then
  echo "Restoring DB backup"
  mv "$BACKUP_DB" togetherly.db || true
fi

echo "E2E run completed. Logs in $LOG_DIR"
exit 0
