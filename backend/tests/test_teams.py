def test_list_teams(get_json, latest_season):
    teams = get_json("/teams")
    assert len(teams) == 30
    assert {t["conference"] for t in teams} == {"East", "West"}
    assert sum(t["conference"] == "East" for t in teams) == 15
    assert all(t["latest"]["season"] == latest_season for t in teams)


def test_team_detail(get_json):
    team = get_json("/teams/okc")  # lower case is accepted
    assert team["abbr"] == "OKC"
    assert team["logo_url"].startswith("https://cdn.nba.com/logos/nba/")
    assert "2024-25" in team["championships"]

    seasons = team["seasons"]
    assert len([s for s in seasons if not s["in_progress"]]) == 26
    assert all(not s["is_champion"] for s in seasons if s["in_progress"])
    assert seasons[0]["team_abbr_then"] == "SEA"
    assert team["total_wins"] == sum(s["wins"] for s in seasons)
    assert team["championships"] == [s["season"] for s in seasons if s["is_champion"]]


def test_roster(get_json):
    roster = get_json("/teams/BOS/roster", season="2023-24")
    players = roster["players"]
    assert roster["season"] == "2023-24"
    assert "Jayson Tatum" in [p["player"]["name"] for p in players]
    assert [p["pts_pg"] for p in players] == sorted((p["pts_pg"] for p in players), reverse=True)


def test_roster_defaults_to_latest_season(get_json, latest_season):
    assert get_json("/teams/BOS/roster")["season"] == latest_season


def test_form_matches_standings(get_json):
    form = get_json("/teams/OKC/form", season="2024-25")
    standings = {s["season"]: s for s in get_json("/teams/OKC")["seasons"]}["2024-25"]
    assert (form["wins"], form["losses"]) == (standings["wins"], standings["losses"])
    assert len(form["games"]) == form["wins"] + form["losses"]
    assert sum(g["won"] for g in form["games"]) == form["wins"]
    assert [g["date"] for g in form["games"]] == sorted(g["date"] for g in form["games"])


def test_team_errors(get_json):
    get_json("/teams/XYZ", status=404)
    get_json("/teams/XYZ/roster", status=404)
    get_json("/teams/XYZ/form", status=404)
    get_json("/teams/BOS/roster", status=404, season="1999-00")
    get_json("/teams/BOS/form", status=404, season="2019-20")  # game logs start in 2020-21
    get_json("/teams/BOSTON", status=422)
    get_json("/teams/BOS/roster", status=422, season="2023-2024")


def test_titles_and_mvps(get_json):
    teams = get_json("/teams")
    detail = get_json("/teams/SAS")
    assert detail["titles"] == len(detail["championships"]) == 4
    assert detail["first_season"] == "2000-01"
    assert [(m["season"], m["player"]["name"]) for m in detail["mvps"]] == [
        ("2001-02", "Tim Duncan"), ("2002-03", "Tim Duncan")]
    # Every completed season has one champion
    completed = [s for s in get_json("/teams/BOS")["seasons"] if not s["in_progress"]]
    assert sum(t["titles"] for t in teams) == len(completed)


def test_franchise_leaders(get_json):
    leaders = get_json("/teams/LAL/leaders", by="points", limit=5)
    assert leaders["since"] == "2000-01"
    rows = leaders["leaders"]
    assert len(rows) == 5
    assert rows[0]["player"]["name"] == "Kobe Bryant"
    assert [r["points"] for r in rows] == sorted((r["points"] for r in rows), reverse=True)
    assert all(abs(r["pts_pg"] - r["points"] / r["games"]) < 0.06 for r in rows)
    assert all(r["first_season"] <= r["last_season"] for r in rows)

    by_games = get_json("/teams/LAL/leaders", by="games")["leaders"]
    assert len(by_games) == 10
    assert [r["games"] for r in by_games] == sorted((r["games"] for r in by_games), reverse=True)


def test_leader_errors(get_json):
    get_json("/teams/XYZ/leaders", status=404)
    get_json("/teams/LAL/leaders", status=422, by="steals")
    get_json("/teams/LAL/leaders", status=422, limit=0)


def test_upcoming_games_for_one_team(get_json):
    games = get_json("/games/upcoming", team="bos")["games"]
    assert all("BOS" in (g["home"]["team"]["abbr"], g["away"]["team"]["abbr"]) for g in games)
    everyone = get_json("/games/upcoming")["games"]
    assert len(games) == sum("BOS" in (g["home"]["team"]["abbr"], g["away"]["team"]["abbr"]) for g in everyone)
