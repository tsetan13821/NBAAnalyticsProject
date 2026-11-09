"""Settings, read from environment variables so the same build runs on any host."""
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = BACKEND_DIR / "data"


@dataclass(frozen=True)
class Settings:
    db_path: Path
    allowed_origins: tuple[str, ...]
    cache_max_age: int  # seconds that clients/CDNs may cache GET responses


def _split(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings(
        db_path=Path(os.getenv("NBA_DB_PATH", DEFAULT_DATA_DIR / "nba.db")),
        allowed_origins=_split(os.getenv("NBA_ALLOWED_ORIGINS", "http://localhost:3000")),
        cache_max_age=int(os.getenv("NBA_CACHE_MAX_AGE", "3600")),
    )
