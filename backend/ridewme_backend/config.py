"""Backend configuration from the shared repo-root `.env`."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
    except ImportError:
        return
    env = REPO_ROOT / ".env"
    if env.exists():
        load_dotenv(env)


@dataclass
class Config:
    host: str = "0.0.0.0"
    port: int = 8080
    ledger_db: str = str(REPO_ROOT / "backend" / "ridewme.db")
    ingest_token: str = ""
    cors_origins: list[str] = None  # type: ignore
    online_timeout_s: float = 15.0

    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]


def load_config() -> Config:
    _load_dotenv()
    db = os.getenv("LEDGER_DB", str(REPO_ROOT / "backend" / "ridewme.db"))
    if not Path(db).is_absolute():
        db = str(REPO_ROOT / db)
    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
    return Config(
        host=os.getenv("BACKEND_BIND", "0.0.0.0"),
        port=int(os.getenv("BACKEND_PORT", "8080")),
        ledger_db=db,
        ingest_token=os.getenv("INGEST_TOKEN", ""),
        cors_origins=origins or ["*"],
    )
