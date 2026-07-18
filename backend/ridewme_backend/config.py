"""Backend configuration from the shared repo-root `.env`."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DSN = "postgresql://ridewme:ridewme@127.0.0.1:5432/ridewme"


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
    database_url: str = DEFAULT_DSN     # local Docker Postgres now, managed cloud later
    ingest_token: str = ""
    cors_origins: list[str] = None  # type: ignore
    online_timeout_s: float = 15.0

    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]


def load_config() -> Config:
    _load_dotenv()
    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
    return Config(
        host=os.getenv("BACKEND_BIND", "0.0.0.0"),
        port=int(os.getenv("BACKEND_PORT", "8080")),
        database_url=os.getenv("DATABASE_URL", DEFAULT_DSN),
        ingest_token=os.getenv("INGEST_TOKEN", ""),
        cors_origins=origins or ["*"],
    )
