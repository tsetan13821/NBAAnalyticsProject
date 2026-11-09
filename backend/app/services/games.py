import sqlite3

from app.errors import NotFoundError
from app.repositories import teams as teams_repo
from app.schemas.games import PredictionRequest
from app.services.tree_model import TreeEnsemble

NO_GAMES_YET = 0.5  # same default the model was trained with


def _team_defaults(conn: sqlite3.Connection, abbr: str, season: str) -> dict:
    form = teams_repo.get_form(conn, abbr, season)
    if form is None:
        return {"win_pct": NO_GAMES_YET, "home_win_pct": NO_GAMES_YET, "road_win_pct": NO_GAMES_YET}
    return {
        "win_pct": form["win_pct"],
        "home_win_pct": form["home_win_pct"] if form["home_win_pct"] is not None else NO_GAMES_YET,
        "road_win_pct": form["road_win_pct"] if form["road_win_pct"] is not None else NO_GAMES_YET,
    }


def predict_game(conn: sqlite3.Connection, model: TreeEnsemble, request: PredictionRequest) -> dict:
    home_abbr, away_abbr = request.home_team.upper(), request.away_team.upper()
    home, away = teams_repo.get_team_ref(conn, home_abbr), teams_repo.get_team_ref(conn, away_abbr)
    for abbr, team in ((home_abbr, home), (away_abbr, away)):
        if team is None:
            raise NotFoundError(f"Team {abbr} not found")

    season = teams_repo.latest_form_season(conn)
    home_defaults, away_defaults = _team_defaults(conn, home_abbr, season), _team_defaults(conn, away_abbr, season)

    def pick(value: float | None, default: float) -> float:
        return default if value is None else value

    inputs = {
        "home_win_pct": pick(request.home_win_pct, home_defaults["win_pct"]),
        "home_home_win_pct": pick(request.home_home_win_pct, home_defaults["home_win_pct"]),
        "away_win_pct": pick(request.away_win_pct, away_defaults["win_pct"]),
        "away_road_win_pct": pick(request.away_road_win_pct, away_defaults["road_win_pct"]),
    }
    home_probability = model.predict_proba({
        "HOME_Overall_WinPCT": inputs["home_win_pct"],
        "HOME_Home_WinPCT": inputs["home_home_win_pct"],
        "AWAY_Overall_WinPCT": inputs["away_win_pct"],
        "AWAY_Away_WinPCT": inputs["away_road_win_pct"],
        "WinPCT_Diff": inputs["home_win_pct"] - inputs["away_win_pct"],
        "HomeAway_Diff": inputs["home_home_win_pct"] - inputs["away_road_win_pct"],
    })
    return {
        "home_team": home,
        "away_team": away,
        "inputs": {**inputs, "defaults_from_season": season},
        "home_win_probability": round(home_probability, 4),
        "away_win_probability": round(1 - home_probability, 4),
        "favorite": home_abbr if home_probability >= 0.5 else away_abbr,
    }
