from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import DatabaseError
from app.main import create_app


@pytest.fixture
def fresh_settings():
    get_settings.cache_clear()
    yield get_settings
    get_settings.cache_clear()


def test_settings_from_environment(monkeypatch, fresh_settings):
    monkeypatch.setenv("NBA_DB_PATH", "/data/other.db")
    monkeypatch.setenv("NBA_ALLOWED_ORIGINS", "https://a.example, https://b.example,")
    monkeypatch.setenv("NBA_CACHE_MAX_AGE", "60")
    settings = fresh_settings()
    assert settings.db_path == Path("/data/other.db")
    assert settings.allowed_origins == ("https://a.example", "https://b.example")
    assert settings.cache_max_age == 60


def test_startup_fails_without_database(settings, tmp_path):
    app = create_app(replace(settings, db_path=tmp_path / "missing.db"))
    with pytest.raises(DatabaseError, match="python -m src.export_db"), TestClient(app):
        pass
