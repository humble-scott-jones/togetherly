#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate || true
python3 -m pip install -r requirements.txt
# By default run unit tests only. To run UI smoke tests set RUN_UI_SMOKE=1
if [ -n "${RUN_UI_SMOKE:-}" ]; then
	echo "Running UI smoke tests (RUN_UI_SMOKE=${RUN_UI_SMOKE})"
	PYTHONPATH=. pytest -q -m ui "$@"
else
	PYTHONPATH=. pytest -q "$@"
fi
