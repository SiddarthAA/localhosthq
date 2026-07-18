"""ridewme backend — dumb collector + tamper-evident ledger + relay.

No CV, no decisions. It verifies signed events, appends them to the SQLite
signature chain, holds current per-driver state, and fans out to the fleet app.
See CONTRACT.md (repo root) — this implements §4 (ingest) and §5 (fleet API).
"""

__version__ = "0.1.0"
