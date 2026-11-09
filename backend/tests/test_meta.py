import re

from app.db import EXPECTED_SCHEMA_VERSION


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["schema_version"] == EXPECTED_SCHEMA_VERSION
    assert response.headers["cache-control"] == "no-store"


def test_meta(get_json):
    meta = get_json("/meta")
    assert meta["first_season"] == "2000-01"
    assert meta["mvp_model"]["seasons"] == 26
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["rosters_as_of"])
    model = meta["next_game_model"]
    assert 0.5 < model["accuracy"] < 1
    assert model["test_season"] == "2025-26"
    assert (model["train_first_season"], model["train_last_season"]) == ("2020-21", "2024-25")
    assert model["train_games"] > 4 * model["test_games"]


def test_meta_separates_completed_and_current_seasons(get_json):
    meta = get_json("/meta")
    assert meta["last_season"] == "2025-26"  # the last completed season: what the models use
    if meta["current_season"]:
        assert meta["current_season"] > meta["last_season"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["current_season_as_of"])


def test_seasons(get_json):
    seasons = get_json("/seasons")
    completed = [s for s in seasons if not s["in_progress"]]
    assert len(completed) == 26
    assert len(seasons) - len(completed) <= 1
    assert all(s["champion"] is None and s["mvp"] is None for s in seasons if s["in_progress"])
    assert [s["season"] for s in seasons] == sorted((s["season"] for s in seasons), reverse=True)  # newest first
    by_season = {s["season"]: s for s in seasons}
    assert by_season["2024-25"]["champion"]["abbr"] == "OKC"
    assert by_season["2022-23"]["mvp"]["name"] == "Joel Embiid"


def test_root_redirects_to_docs(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_successful_gets_are_cacheable(client, settings):
    response = client.get("/api/v1/teams")
    assert response.headers["cache-control"] == f"public, max-age={settings.cache_max_age}"


def test_errors_are_not_cached(client):
    assert client.get("/api/v1/teams/XYZ").headers["cache-control"] == "no-store"
    assert client.get("/api/v1/players/abc").headers["cache-control"] == "no-store"


def test_unknown_route_is_404(client):
    assert client.get("/api/v1/nope").status_code == 404


def test_cors_allows_configured_origin(client, settings):
    origin = settings.allowed_origins[0]
    response = client.options(
        "/api/v1/games/predict",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_rejects_other_origins(client):
    response = client.get("/api/v1/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers
