import json
import sqlite3
from collections import defaultdict

from app.repositories.refs import team_columns, team_ref
from app.urls import headshot_url

KEY_ABSENCE_MIN_VALUE = 1.0  # points of Game Score; below this an absence is not worth a mention
KEY_ABSENCES_PER_GAME = 4
ALREADY_MISSING_BELOW = 0.5  # played fewer than half of the team's last ten games

_GAME_SELECT = f"""
    SELECT g.*, {team_columns('h', 'h_')}, {team_columns('a', 'a_')}
    FROM game_predictions g
    JOIN franchises h ON h.abbr = g.home_abbr
    JOIN franchises a ON a.abbr = g.away_abbr
"""


def _side(row: sqlite3.Row, side: str) -> dict:
    prefix = side[0] + "_"
    return {
        "team": team_ref(row, prefix), "wins": row[f"{side}_wins"], "losses": row[f"{side}_losses"],
        "elo": row[f"{side}_elo"],
    }


def _summary(row: sqlite3.Row, absences: list[dict]) -> dict:
    prob = row["home_win_prob"]
    home, away = row["home_abbr"], row["away_abbr"]
    result = None
    if row["played"]:
        home_won = row["home_pts"] > row["away_pts"]
        result = {
            "home_pts": row["home_pts"], "away_pts": row["away_pts"], "winner": home if home_won else away,
            "correct": (prob >= 0.5) == home_won,
        }
    return {
        "game_id": row["game_id"], "season": row["season"], "date": row["game_date"], "tip_et": row["tip_et"],
        "home": _side(row, "home"), "away": _side(row, "away"),
        "home_win_probability": prob, "predicted_margin": round(row["pred_margin"], 1),
        "favorite": home if prob >= 0.5 else away, "result": result, "key_absences": absences,
    }


def _absences(conn: sqlite3.Connection, game_ids: list[str]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    if not game_ids:
        return out
    marks = ", ".join("?" for _ in game_ids)
    rows = conn.execute(
        f"""SELECT game_id, team_abbr, player_id, name, status, participation, value * (1 - chance) AS value_lost
            FROM game_players
            WHERE game_id IN ({marks}) AND status IN ('Out', 'Doubtful', 'Questionable') AND value * (1 - chance) >= ?
            ORDER BY game_id, value_lost DESC""",
        (*game_ids, KEY_ABSENCE_MIN_VALUE),
    )
    for r in rows:
        if len(out[r["game_id"]]) < KEY_ABSENCES_PER_GAME:
            out[r["game_id"]].append({
                "player_id": r["player_id"], "name": r["name"], "team_abbr": r["team_abbr"], "status": r["status"],
                "value_lost": round(r["value_lost"], 1), "already_missing": r["participation"] < ALREADY_MISSING_BELOW,
            })
    return out


def _summaries(conn: sqlite3.Connection, rows: list[sqlite3.Row]) -> list[dict]:
    absences = _absences(conn, [r["game_id"] for r in rows])
    return [_summary(r, absences.get(r["game_id"], [])) for r in rows]


def list_upcoming(conn: sqlite3.Connection, team: str | None = None) -> list[dict]:
    where, params = "g.played = 0", []
    if team:
        where += " AND ? IN (g.home_abbr, g.away_abbr)"
        params.append(team)
    rows = conn.execute(
        f"{_GAME_SELECT} WHERE {where} ORDER BY g.game_date, g.tip_et, g.game_id", params
    ).fetchall()
    return _summaries(conn, rows)


def list_results(conn: sqlite3.Connection, team: str | None, limit: int, offset: int) -> tuple[list[dict], int]:
    where, params = "g.played = 1", []
    if team:
        where += " AND ? IN (g.home_abbr, g.away_abbr)"
        params.append(team)
    total = conn.execute(f"SELECT COUNT(*) FROM game_predictions g WHERE {where}", params).fetchone()[0]
    rows = conn.execute(
        f"{_GAME_SELECT} WHERE {where} ORDER BY g.game_date DESC, g.game_id DESC LIMIT ? OFFSET ?",
        (*params, limit, offset),
    ).fetchall()
    return _summaries(conn, rows), total


def played_outcomes(conn: sqlite3.Connection, team: str | None) -> list[tuple[float, int]]:
    """(home win probability, home won) for every played game."""
    where, params = "played = 1", []
    if team:
        where += " AND ? IN (home_abbr, away_abbr)"
        params.append(team)
    return [
        (r[0], int(r[1] > r[2]))
        for r in conn.execute(f"SELECT home_win_prob, home_pts, away_pts FROM game_predictions WHERE {where}", params)
    ]


def current_season(conn: sqlite3.Connection) -> str | None:
    return conn.execute("SELECT MAX(season) FROM game_predictions").fetchone()[0]


def get_game(conn: sqlite3.Connection, game_id: str) -> tuple[dict, dict] | None:
    """The game's summary and its model inputs."""
    row = conn.execute(f"{_GAME_SELECT} WHERE g.game_id = ?", (game_id,)).fetchone()
    if row is None:
        return None
    return _summaries(conn, [row])[0], json.loads(row["features"])


def get_players(conn: sqlite3.Connection, game_id: str) -> list[dict]:
    """Every rostered player, most valuable first. rate_above and minutes are kept for what-if changes."""
    return [
        {
            "id": r["player_id"], "name": r["name"], "headshot_url": headshot_url(r["player_id"]),
            "team_abbr": r["team_abbr"], "value": round(r["value"], 2),
            "rate_above": r["rate_above"], "minutes": r["expected_minutes"],
            "expected_minutes": round(r["expected_minutes"], 1), "participation": r["participation"],
            "status": r["status"], "reason": r["reason"], "status_source": r["status_source"],
            "chance": r["chance"], "played": None if r["played"] is None else bool(r["played"]), "what_if": None,
        }
        for r in conn.execute(
            "SELECT * FROM game_players WHERE game_id = ? ORDER BY value DESC, player_id", (game_id,)
        )
    ]
