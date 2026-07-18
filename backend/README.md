# backend — ridewme relay hub

Thin FastAPI relay hub: ingests signed events + the sensor stream, stores the tamper-evident audit
log, and broadcasts to the fleet app. **No CV, no decisions — dumb relay + ledger.** Every "where
does this go?" reduces to: raw data or judgment → daemon; storage/relay → here; display → frontend.

## Run

```bash
../setup.sh          # one-time: shared root .venv + deps
./run.sh             # serves 0.0.0.0:${BACKEND_PORT:-8080}
```

## API — see [`../CONTRACT.md`](../CONTRACT.md) §5 (build the frontend against this)

| | endpoint | purpose |
|---|----------|---------|
| WS  | `/ws/fleet` | live driver states + event feed (fleet app subscribes) |
| WS  | `/ws/ingest` | daemon uplink (signed events in) |
| GET | `/api/drivers` · `/api/drivers/{id}` | current per-driver state |
| GET | `/api/drivers/{id}/events?type=&limit=` | event history |
| GET | `/api/incidents` | crash incident cards |
| GET | `/api/drivers/{id}/ledger/verify` | chain verification (the tamper demo) |
| GET | `/api/drivers/{id}/ledger` | raw signed chain for the log view |

Ledger: SQLite + Ed25519 signature chain (`ridewme_backend/ledger.py`). Verification is
recomputed from stored bytes, so editing any row makes `…/ledger/verify` report the broken seq.

## Tests

```bash
VIRTUAL_ENV=../.venv uv pip install -r ../requirements-dev.txt
../.venv/bin/python -m pytest tests
```
