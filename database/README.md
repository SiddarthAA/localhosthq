# database — local Postgres for the ledger

The backend's tamper-evident audit ledger lives in Postgres. Local dev runs it in Docker;
at deploy time you point `DATABASE_URL` at managed Postgres (Supabase / RDS / Neon) — **same
schema, different DSN**. The backend Docker image itself comes later.

## Run

```bash
cd database
docker compose up -d          # start Postgres on :5432 (creds from ../.env or the defaults)
docker compose ps             # check health
docker compose logs -f postgres
docker compose down           # stop (KEEPS data — persistent volume)
docker compose down -v        # stop + wipe the ledger
```

The backend reads `DATABASE_URL` from the repo-root `.env`
(default `postgresql://ridewme:ridewme@127.0.0.1:5432/ridewme`) and creates the tables on
startup, so it works whether or not `init/01_schema.sql` pre-ran.

## Files
- `docker-compose.yml` — the Postgres service + a persistent named volume.
- `init/01_schema.sql` — `sessions` + `events` tables, auto-applied on first boot.

## Schema (see `init/01_schema.sql`)
- **`sessions`** — one per daemon run; pins the Ed25519 `pubkey`.
- **`events`** — the signed chain; `body` is the exact signed JSON (TEXT) so
  `GET /api/drivers/{id}/ledger/verify` recomputes from stored bytes and catches any tamper.

## Connect manually
```bash
docker exec -it ridewme-postgres psql -U ridewme -d ridewme
# \dt   list tables   ·   SELECT type, count(*) FROM events GROUP BY type;
```
