import pytest

from app.repositories.players import METRIC_FIELDS
from app.services.players import METRICS

LEBRON, CURRY, JOKIC, JORDAN, WEMBANYAMA, TATUM = 2544, 201939, 203999, 893, 1641705, 1628369


# --- search -----------------------------------------------------------------------------------------

def test_search_ignores_accents_and_case(get_json):
    for query in ("jokic", "JOKIĆ", "  Nikola   Jokic "):
        page = get_json("/players", q=query)
        assert [p["id"] for p in page["items"]] == [JOKIC], query


def test_search_ranks_name_starts_first(get_json):
    # "curry" matches several players; the ones whose first or last name starts with it come first.
    page = get_json("/players", q="curry")
    assert page["total"] >= 2
    first = page["items"][0]["name"].lower().split()
    assert any(part.startswith("curry") for part in first)
    assert CURRY in [p["id"] for p in page["items"]]


def test_search_treats_like_wildcards_literally(get_json):
    assert get_json("/players", q="%")["total"] == 0
    assert get_json("/players", q="_")["total"] == 0


def test_search_pagination(get_json):
    first = get_json("/players", limit=5, offset=0)
    second = get_json("/players", limit=5, offset=5)
    assert first["total"] == second["total"] > 1000
    assert len(first["items"]) == len(second["items"]) == 5
    assert not {p["id"] for p in first["items"]} & {p["id"] for p in second["items"]}


def test_search_filters(get_json):
    roster = get_json("/players", team="bos", season="2023-24", limit=100)
    assert TATUM in [p["id"] for p in roster["items"]]
    assert 10 <= roster["total"] <= 25

    centers = get_json("/players", position_group="C", limit=100)
    assert {p["position_group"] for p in centers["items"]} == {"C"}


def test_search_returns_summary_shape(get_json):
    player = get_json("/players", q="lebron")["items"][0]
    assert player["id"] == LEBRON
    assert player["first_season"] == "2003-04"
    assert player["latest_team"]["abbr"] in {"LAL", "PHI"}  # his team in his newest season in the data
    assert player["headshot_url"].endswith(f"/{LEBRON}.png")


def test_current_team_is_separate_from_last_team_in_data(get_json):
    # Rosters change with every refresh, so check the shape rather than a particular player's team.
    tim_duncan = get_json("/players", q="tim duncan")["items"][0]
    assert tim_duncan["current_team"] is None
    assert tim_duncan["latest_team"]["abbr"] == "SAS"

    recent = get_json("/players", season="2025-26", limit=100)["items"]
    on_roster = [p for p in recent if p["current_team"]]
    assert len(on_roster) > 50
    assert set(on_roster[0]["current_team"]) == set(on_roster[0]["latest_team"])


@pytest.mark.parametrize("params", [
    {"q": "x" * 51}, {"limit": 0}, {"limit": 101}, {"offset": -1}, {"season": "2023"}, {"position_group": "PG"},
])
def test_search_rejects_invalid_params(get_json, params):
    get_json("/players", status=422, **params)


# --- profile ----------------------------------------------------------------------------------------

def test_profile(get_json):
    profile = get_json(f"/players/{LEBRON}")
    assert profile["name"] == "LeBron James"
    assert profile["draft_number"] == 1
    assert profile["mvp_seasons"] == ["2008-09", "2009-10", "2011-12", "2012-13"]

    seasons = profile["seasons"]
    assert [s["season"] for s in seasons] == sorted(s["season"] for s in seasons)
    assert profile["seasons_played"] == len(seasons)
    assert profile["career"]["games"] == sum(s["games"] for s in seasons)
    weighted_pts = sum(s["pts_pg"] * s["games"] for s in seasons) / profile["career"]["games"]
    assert profile["career"]["pts_pg"] == pytest.approx(weighted_pts, abs=0.01)


def test_profile_marks_the_season_in_progress(get_json, latest_season):
    seasons = get_json(f"/players/{LEBRON}")["seasons"]
    assert [s["season"] for s in seasons if s["in_progress"]] in ([], [latest_season])
    assert not any(s["in_progress"] for s in seasons[:-1])


def test_profile_keeps_historical_abbreviation(get_json):
    # Kevin Durant's rookie season was in Seattle, which is now OKC.
    seasons = get_json("/players/201142")["seasons"]
    assert (seasons[0]["team_abbr"], seasons[0]["team_abbr_then"]) == ("OKC", "SEA")


def test_profile_errors(get_json):
    get_json("/players/1", status=404)
    get_json("/players/0", status=422)


# --- similar players --------------------------------------------------------------------------------

def test_similar_players(get_json):
    result = get_json(f"/players/{JOKIC}/similar")
    assert result["season"] == "2025-26"
    assert result["player"]["id"] == JOKIC
    similar = result["similar"]
    assert similar and JOKIC not in [s["player"]["id"] for s in similar]
    assert [s["rank"] for s in similar] == list(range(1, len(similar) + 1))
    assert [s["distance"] for s in similar] == sorted(s["distance"] for s in similar)


def test_similar_players_for_a_season(get_json):
    assert get_json(f"/players/{LEBRON}/similar", season="2012-13")["season"] == "2012-13"


def test_similar_players_without_archetype_is_404(get_json):
    get_json(f"/players/{LEBRON}/similar", status=404, season="2001-02")  # before his rookie year


# --- compare ----------------------------------------------------------------------------------------

def test_metrics_match_repository_fields():
    assert [m["key"] for m in METRICS] != []
    assert sorted(m["key"] for m in METRICS) == sorted(METRIC_FIELDS)


def test_compare_defaults_to_latest_common_season(client, latest_season):
    response = client.get("/api/v1/players/compare", params={"ids": [CURRY, LEBRON]})
    assert response.status_code == 200
    body = response.json()
    assert body["season"] == latest_season
    assert [p["player"]["id"] for p in body["players"]] == [CURRY, LEBRON]
    for player in body["players"]:
        assert player["peer_group"] == "ALL"
        assert set(player["stats"]) == set(player["percentiles"]) == set(METRIC_FIELDS)
        assert all(0 <= value <= 100 for value in player["percentiles"].values())


def test_compare_by_position(client):
    params = {"ids": [CURRY, JOKIC], "season": "2022-23", "peer_group": "POSITION"}
    body = client.get("/api/v1/players/compare", params=params).json()
    assert [p["peer_group"] for p in body["players"]] == ["G", "C"]


@pytest.mark.parametrize(("params", "status"), [
    ({"ids": [CURRY]}, 422),  # need at least two
    ({"ids": [1, 2, 3, 4, 5]}, 422),  # at most four
    ({"ids": [JORDAN, WEMBANYAMA]}, 404),  # never in the league together
    ({"ids": [CURRY, WEMBANYAMA], "season": "2015-16"}, 404),  # one of them missing that season
    ({"ids": [CURRY, LEBRON], "peer_group": "TEAM"}, 422),
])
def test_compare_errors(client, params, status):
    assert client.get("/api/v1/players/compare", params=params).status_code == status
