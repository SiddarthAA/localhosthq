#!/usr/bin/env bash
# Start the ridewme backend (dumb relay + tamper-evident ledger) on the shared venv.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d .venv ] || { echo "shared .venv missing — run ./setup.sh first"; exit 1; }
exec ./.venv/bin/python backend/main.py "$@"
