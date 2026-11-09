"""The API tests run against the real serving database, built with `python -m src.export_db`."""
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture(scope="session")
def settings():
    settings = replace(get_settings(), allowed_origins=("http://localhost:3000",), cache_max_age=600)
    for path in (settings.db_path, settings.model_path):
        if not path.exists():
            pytest.fail(f"{path} is missing. Build it from the repo root with: python -m src.export_db", pytrace=False)
    return settings


@pytest.fixture(scope="session")
def client(settings):
    # The context manager runs the lifespan, which loads the database metadata and the model.
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def get_json(client):
    """GET a path under /api/v1, assert the expected status and return the JSON body."""

    def get(path: str, status: int = 200, **params):
        response = client.get(f"/api/v1{path}", params=params)
        assert response.status_code == status, response.text
        return response.json()

    return get


@pytest.fixture(scope="session")
def latest_season(client):
    """The newest season in the data: the one under way if its stats are included, else the last completed one.

    Tests use this instead of a hard-coded season, so they keep passing when the data is refreshed.
    """
    meta = client.get("/api/v1/meta").json()
    return meta["current_season"] or meta["last_season"]
