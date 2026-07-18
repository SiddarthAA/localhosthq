#!/usr/bin/env bash
# Start the ridewme edge daemon on the shared venv.
#   ./cli/run.sh              phone camera + phone sensors (needs sensor-app up)
#   ./cli/run.sh --sim        fully offline: scripted drowsy + crash scenario
#   ./cli/run.sh --naive      strawman per-blink detector (demo contrast)
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d .venv ] || { echo "shared .venv missing — run ./setup.sh first"; exit 1; }
exec ./.venv/bin/python cli/main.py "$@"
