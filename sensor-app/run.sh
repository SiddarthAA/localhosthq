#!/usr/bin/env bash
# Start the sensor-app ingest server on shawarma.
# First run creates a uv venv and installs deps; subsequent runs just launch.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Creating uv venv and installing dependencies…"
  uv venv .venv --python 3.12
  VIRTUAL_ENV=.venv uv pip install -r requirements.txt
fi

exec ./.venv/bin/uvicorn server.main:app --host 0.0.0.0 --port 8000
