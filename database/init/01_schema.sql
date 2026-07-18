-- ridewme tamper-evident audit ledger — schema.
-- Auto-applied by the postgres container on first boot (docker-entrypoint-initdb.d).
-- The backend also runs these idempotently on startup, so it works with any Postgres.

-- One row per daemon run; pins the session's Ed25519 public key.
CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    driver_id   TEXT NOT NULL,
    pubkey      TEXT NOT NULL,
    started_at  DOUBLE PRECISION
);

-- The signed event chain. `body` is the EXACT signed JSON (TEXT, not JSONB) so
-- verification recomputes canonical bytes from the stored bytes — editing any row
-- makes /ledger/verify report the broken seq. prev_sig links each event to the last.
CREATE TABLE IF NOT EXISTS events (
    session_id  TEXT NOT NULL,
    seq         INTEGER NOT NULL,
    driver_id   TEXT,
    type        TEXT,
    ts          DOUBLE PRECISION,
    prev_sig    TEXT,
    sig         TEXT,
    body        TEXT NOT NULL,
    verified    BOOLEAN,
    PRIMARY KEY (session_id, seq)
);

CREATE INDEX IF NOT EXISTS idx_events_driver ON events (driver_id, ts);
CREATE INDEX IF NOT EXISTS idx_events_dtype  ON events (driver_id, type, ts);
