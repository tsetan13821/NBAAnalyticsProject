def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["schema_version"] == 1
    assert response.headers["cache-control"] == "no-store"


def test_meta(get_json):
    meta = get_json("/meta")
    assert meta["first_season"] == "2000-01"
    assert meta["mvp_model"]["seasons"] == 26
    model = meta["next_game_model"]
    assert 0.5 < model["accuracy"] < 1
    assert model["test_season"] == "2025-26"


def test_seasons(get_json):
    seasons = get_json("/seasons")
    assert len(seasons) == 26
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
