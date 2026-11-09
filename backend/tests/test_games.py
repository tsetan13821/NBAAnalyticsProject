import pytest


def predict(client, **body):
    return client.post("/api/v1/games/predict", json=body)


def test_predict_with_season_defaults(client, get_json):
    response = predict(client, home_team="bos", away_team="DAL")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"

    body = response.json()
    assert body["home_team"]["abbr"] == "BOS"
    assert body["away_team"]["abbr"] == "DAL"
    assert body["home_win_probability"] + body["away_win_probability"] == pytest.approx(1, abs=1e-4)
    assert body["favorite"] == ("BOS" if body["home_win_probability"] >= 0.5 else "DAL")

    # Omitted inputs come from each team's final record in the latest season.
    inputs = body["inputs"]
    form = get_json("/teams/BOS/form", season=inputs["defaults_from_season"])
    assert inputs["home_win_pct"] == form["win_pct"]
    assert inputs["home_home_win_pct"] == form["home_win_pct"]


def test_predict_uses_given_inputs(client):
    strong = {"home_win_pct": 0.9, "home_home_win_pct": 0.95, "away_win_pct": 0.2, "away_road_win_pct": 0.1}
    weak = {"home_win_pct": 0.2, "home_home_win_pct": 0.25, "away_win_pct": 0.9, "away_road_win_pct": 0.85}

    favored = predict(client, home_team="BOS", away_team="DAL", **strong).json()
    assert favored["inputs"] | strong == favored["inputs"]
    assert favored["home_win_probability"] > 0.8
    assert favored["favorite"] == "BOS"

    underdog = predict(client, home_team="BOS", away_team="DAL", **weak).json()
    assert underdog["home_win_probability"] < 0.3
    assert underdog["favorite"] == "DAL"


def test_partial_inputs_fill_the_rest_from_defaults(client):
    default = predict(client, home_team="BOS", away_team="DAL").json()["inputs"]
    partial = predict(client, home_team="BOS", away_team="DAL", away_win_pct=0.5).json()["inputs"]
    assert partial["away_win_pct"] == 0.5
    assert partial["home_win_pct"] == default["home_win_pct"]


@pytest.mark.parametrize(("body", "status"), [
    ({"home_team": "BOS", "away_team": "bos"}, 422),  # same team
    ({"home_team": "BOS"}, 422),  # missing away team
    ({"home_team": "BOS", "away_team": "DAL", "home_win_pct": 1.2}, 422),
    ({"home_team": "BOS", "away_team": "DAL", "away_road_win_pct": -0.1}, 422),
    ({"home_team": "BOS", "away_team": "XYZ"}, 404),
])
def test_predict_errors(client, body, status):
    response = predict(client, **body)
    assert response.status_code == status, response.text
    if status == 404:
        assert response.json() == {"detail": "Team XYZ not found"}


def test_predict_is_post_only(client):
    assert client.get("/api/v1/games/predict").status_code == 405
