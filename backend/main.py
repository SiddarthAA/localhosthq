"""ridewme backend — entrypoint. Dumb relay + tamper-evident ledger.

    python backend/main.py        # serves 0.0.0.0:${BACKEND_PORT:-8080}
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # make `ridewme_backend` importable

from ridewme_backend.app import create_app  # noqa: E402
from ridewme_backend.config import load_config  # noqa: E402


def main() -> None:
    import uvicorn

    cfg = load_config()
    app = create_app(cfg)
    db = cfg.database_url.rsplit("@", 1)[-1]  # redact credentials in logs
    print(f"[backend] serving http://{cfg.host}:{cfg.port}  db=postgres://…@{db}")
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")


if __name__ == "__main__":
    main()
