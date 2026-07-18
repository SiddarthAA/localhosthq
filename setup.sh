#!/usr/bin/env bash
# One-time setup: shared uv venv for backend + cli (mirrors the sensor-app convention).
set -euo pipefail
cd "$(dirname "$0")"

[ -d .venv ] || uv venv .venv --python 3.12
VIRTUAL_ENV=.venv uv pip install -r backend/requirements.txt -r cli/requirements.txt
echo
echo "shared .venv ready (backend + cli)."
echo "  dev/test deps:  VIRTUAL_ENV=.venv uv pip install -r requirements-dev.txt"
echo "  run backend:    ./backend/run.sh"
echo "  run daemon:     ./cli/run.sh --sim        (offline demo; no sensor server needed)"
