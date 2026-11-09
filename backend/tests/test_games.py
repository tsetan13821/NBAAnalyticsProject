"""Game predictions. The data is whatever the last `python -m src.game_model.live` produced, so the tests
check invariants rather than particular games."""
import math

import pytest

from app.services.game_model import capped_value, win_probability


@pytest.fixture(scope="module")
def upcoming(client):
    return client.get("/api/v1/games/upcoming").json()


@pytest.fixture(scope="module")
def results(client):
    return client.get("/api/v1/games/results", params={"limit": 100}).json()


@pytest.fixture(scope="module")
def a_game(upcoming, results):
    games = upcoming["games"] or results["items"]
    if not games:
        pytest.skip("No season in progress in this build")
    return games[0]


def test_upcoming_games_are_unplayed_and_in_order(upcoming):
    games = upcoming["games"]
    assert all(g["result"] is None for g in games)
    assert [(g["date"], g["tip_et"] or "") for g in games] == sorted((g["date"], g["tip_et"] or "") for g in games)
    for g in games:
        assert 0 < g["home_win_probability"] < 1
        assert (g["home_win_probability"] >= 0.5) == (g["predicted_margin"] >= 0) or abs(g["predicted_margin"]) < 0.1
        assert g["favorite"] in (g["home"]["team"]["abbr"], g["away"]["team"]["abbr"])
        assert len(g["key_absences"]) <= 4
        assert all(a["team_abbr"] in (g["home"]["team"]["abbr"], g["away"]["team"]["abbr"]) for a in g["key_absences"])


def test_results_are_newest_first_with_a_track_record(results):
    items = results["items"]
    assert [g["date"] for g in items] == sorted((g["date"] for g in items), reverse=True)
    assert all(g["result"] is not None for g in items)
    record = results["record"]
    assert record["games"] == results["total"]
    if record["games"]:
        assert record["correct"] == round(record["accuracy"] * record["games"])
        assert sum(b["games"] for b in record["by_confidence"]) == record["games"]
        assert sum(b["favorite_won"] for b in record["by_confidence"]) == record["correct"]
        page = items[: record["games"]]
        assert all(g["result"]["correct"] == (g["result"]["winner"] == g["favorite"]) for g in page)


def test_results_for_one_team(get_json, a_game):
    abbr = a_game["home"]["team"]["abbr"]
    body = get_json("/games/results", team=abbr.lower(), limit=5)
    assert all(abbr in (g["home"]["team"]["abbr"], g["away"]["team"]["abbr"]) for g in body["items"])
    assert body["record"]["games"] == body["total"]


def test_game_detail_explains_the_prediction(get_json, a_game):
    game = get_json(f"/games/{a_game['game_id']}")
    # The detail recomputes the prediction from the stored inputs: it must match the list
    assert game["home_win_probability"] == pytest.approx(a_game["home_win_probability"], abs=2e-3)
    assert sum(item["points"] for item in game["breakdown"]) == pytest.approx(game["predicted_margin"], abs=0.1)
    assert win_probability(game["predicted_margin"], game["spread"]) == pytest.approx(
        game["home_win_probability"], abs=5e-3
    )
    assert [i["key"] for i in game["breakdown"]][0] == "home"
    assert game["what_if"] is None
    for side in ("home", "away"):
        players = game[f"{side}_players"]
        assert players, side
        assert all(p["team_abbr"] == game[side]["team"]["abbr"] for p in players)
        assert [p["value"] for p in players] == sorted((p["value"] for p in players), reverse=True)
        assert all(0 <= p["chance"] <= 1 for p in players)


def test_sitting_a_star_lowers_his_teams_chances(get_json, a_game):
    base = get_json(f"/games/{a_game['game_id']}")
    star = max(base["home_players"], key=lambda p: p["value"] * p["chance"])
    benched = get_json(f"/games/{a_game['game_id']}", out=[star["id"]])
    assert benched["home_win_probability"] < base["home_win_probability"]
    assert benched["what_if"]["base_home_win_probability"] == base["home_win_probability"]
    assert benched["what_if"]["out"] == [star["id"]]
    changed = next(p for p in benched["home_players"] if p["id"] == star["id"])
    assert (changed["chance"], changed["what_if"]) == (0.0, "out")
    # Only the availability input moves
    before = {i["key"]: i["points"] for i in base["breakdown"]}
    after = {i["key"]: i["points"] for i in benched["breakdown"]}
    assert {k for k in before if before[k] != after[k]} == {"availability"}


def test_playing_an_injured_player_helps(get_json, a_game):
    base = get_json(f"/games/{a_game['game_id']}")
    doubtful = [p for p in base["away_players"] if p["chance"] < 1 and p["value"] > 0]
    if not doubtful:
        pytest.skip("Nobody on the away team is doubtful for this game")
    back = get_json(f"/games/{a_game['game_id']}", **{"in": [doubtful[0]["id"]]})
    assert back["home_win_probability"] <= base["home_win_probability"]


def test_what_if_rejects_strangers_and_contradictions(client, a_game):
    path = f"/api/v1/games/{a_game['game_id']}"
    assert client.get(path, params={"out": 1}).status_code == 400
    detail = client.get(path).json()
    pid = detail["home_players"][0]["id"]
    response = client.get(path, params={"out": pid, "in": pid})
    assert response.status_code == 400
    assert "both out and in" in response.json()["detail"]


def test_unknown_and_malformed_games(client):
    assert client.get("/api/v1/games/0099999999").status_code == 404
    assert client.get("/api/v1/games/abc").status_code == 422


def test_model_details(get_json):
    model = get_json("/games/model")
    evaluation = model["evaluation"]
    assert evaluation["held_out"]["accuracy"] > evaluation["baselines"]["better_record"]
    assert evaluation["held_out"]["log_loss"] < evaluation["baselines"]["elo"]["log_loss"]
    assert {f["group"] for f in model["features"]} >= {"strength", "availability"}
    assert model["play_rates"]["Out"] < 0.02
    assert 0 < model["play_rates"]["Questionable"] < 1
    assert [s["added"] for s in evaluation["ablation"]][:2] == ["strength", "home"]


def test_capped_value_gives_minutes_to_the_best_players_first():
    # Two 200-minute players: only 240 minutes exist, so the better one plays all of his
    assert capped_value([(0.1, 200, 1), (0.5, 200, 1)]) == pytest.approx(0.5 * 200 + 0.1 * 40)
    assert capped_value([(0.5, 200, 0), (0.1, 200, 1)]) == pytest.approx(0.1 * 200)
    assert capped_value([]) == 0


def test_win_probability_is_symmetric():
    assert win_probability(0, 12) == 0.5
    assert win_probability(5, 12) + win_probability(-5, 12) == pytest.approx(1)
    assert win_probability(12, 12) == pytest.approx(0.5 * (1 + math.erf(1 / math.sqrt(2))))
