import sqlite3

from app.repositories.refs import player_columns, player_ref, team_columns, team_ref

_TEAM_SELECT = f"""
    SELECT {team_columns('f', 't_')}, f.city, f.nickname, f.conference,
           ts.season AS latest_season, ts.wins, ts.losses, ts.win_pct, ts.conference_rank, ts.point_diff_pg,
           s.in_progress,
           (SELECT COUNT(*) FROM team_seasons c WHERE c.team_abbr = f.abbr AND c.is_champion = 1) AS titles
    FROM franchises f
    JOIN team_seasons ts ON ts.team_abbr = f.abbr
     AND ts.season = (SELECT MAX(season) FROM team_seasons WHERE team_abbr = f.abbr)
    JOIN seasons s ON s.season = ts.season
"""


def _summary(row: sqlite3.Row) -> dict:
    return {
        **team_ref(row, "t_"),
        "city": row["city"],
        "nickname": row["nickname"],
        "conference": row["conference"],
        "latest": {
            "season": row["latest_season"], "wins": row["wins"], "losses": row["losses"],
            "win_pct": row["win_pct"], "conference_rank": row["conference_rank"],
            "point_diff_pg": row["point_diff_pg"], "in_progress": bool(row["in_progress"]),
        },
        "titles": row["titles"],
    }


def get_team_ref(conn: sqlite3.Connection, abbr: str) -> dict | None:
    row = conn.execute(f"SELECT {team_columns('f', 't_')} FROM franchises f WHERE f.abbr = ?", (abbr,)).fetchone()
    return team_ref(row, "t_") if row else None


def list_teams(conn: sqlite3.Connection) -> list[dict]:
    return [_summary(r) for r in conn.execute(f"{_TEAM_SELECT} ORDER BY f.conference, f.name")]


def get_team(conn: sqlite3.Connection, abbr: str) -> dict | None:
    row = conn.execute(f"{_TEAM_SELECT} WHERE f.abbr = ?", (abbr,)).fetchone()
    if row is None:
        return None
    seasons = [
        {**dict(s), "is_champion": bool(s["is_champion"]), "in_progress": bool(s["in_progress"])}
        for s in conn.execute(
            """SELECT ts.season, ts.team_abbr_then, ts.conference, ts.conference_rank, ts.wins, ts.losses,
                      ts.win_pct, ts.point_diff_pg, ts.is_champion, s.in_progress
               FROM team_seasons ts JOIN seasons s USING (season) WHERE ts.team_abbr = ? ORDER BY ts.season""",
            (abbr,),
        )
    ]
    mvps = conn.execute(
        f"""SELECT s.season, {player_columns('p', 'p_')}
            FROM seasons s
            JOIN player_seasons ps ON ps.player_id = s.mvp_player_id AND ps.season = s.season
            JOIN players p ON p.player_id = s.mvp_player_id
            WHERE ps.team_abbr = ? ORDER BY s.season""",
        (abbr,),
    )
    return {
        **_summary(row),
        "first_season": seasons[0]["season"],
        "championships": [s["season"] for s in seasons if s["is_champion"]],
        "total_wins": sum(s["wins"] for s in seasons),
        "total_losses": sum(s["losses"] for s in seasons),
        "seasons": seasons,
        "mvps": [{"season": m["season"], "player": player_ref(m, "p_")} for m in mvps],
    }


# Totals rebuilt from per-game averages (stored unrounded, so they are exact). A player traded during a
# season appears once, with the team he finished it with, so his whole season counts for that team.
_LEADER_ORDER = {"points": "points", "rebounds": "rebounds", "assists": "assists", "games": "games"}


def get_leaders(conn: sqlite3.Connection, abbr: str, by: str, limit: int) -> list[dict]:
    order = _LEADER_ORDER[by]  # a fixed set of column names, never user text
    rows = conn.execute(
        f"""SELECT {player_columns('p', 'p_')}, p.current_team_abbr IS ps.team_abbr AS on_roster,
                   COUNT(*) AS seasons, MIN(ps.season) AS first_season, MAX(ps.season) AS last_season,
                   SUM(ps.games) AS games, SUM(ps.pts_pg * ps.games) AS points,
                   SUM(ps.reb_pg * ps.games) AS rebounds, SUM(ps.ast_pg * ps.games) AS assists
            FROM player_seasons ps JOIN players p USING (player_id)
            WHERE ps.team_abbr = ?
            GROUP BY ps.player_id
            ORDER BY {order} DESC, games DESC, ps.player_id
            LIMIT ?""",
        (abbr, limit),
    ).fetchall()
    return [
        {
            "player": player_ref(r, "p_"), "seasons": r["seasons"],
            "first_season": r["first_season"], "last_season": r["last_season"], "games": r["games"],
            "points": round(r["points"]), "rebounds": round(r["rebounds"]), "assists": round(r["assists"]),
            "pts_pg": round(r["points"] / r["games"], 1) if r["games"] else 0.0,
            "on_roster": bool(r["on_roster"]),
        }
        for r in rows
    ]


def first_season(conn: sqlite3.Connection, abbr: str) -> str | None:
    return conn.execute("SELECT MIN(season) FROM team_seasons WHERE team_abbr = ?", (abbr,)).fetchone()[0]


_ROSTER_FIELDS = ("games", "min_pg", "pts_pg", "reb_pg", "ast_pg", "ts_pct", "archetype", "tier")


def get_roster(conn: sqlite3.Connection, abbr: str, season: str) -> list[dict]:
    rows = conn.execute(
        f"""SELECT {', '.join(f'ps.{f}' for f in _ROSTER_FIELDS)}, {player_columns('p', 'p_')}
            FROM player_seasons ps JOIN players p USING (player_id)
            WHERE ps.team_abbr = ? AND ps.season = ?
            ORDER BY ps.pts_pg DESC""",
        (abbr, season),
    ).fetchall()
    return [
        {"player": player_ref(r, "p_"), **{f: r[f] for f in _ROSTER_FIELDS}}
        for r in rows
    ]


def latest_season(conn: sqlite3.Connection, abbr: str) -> str | None:
    return conn.execute("SELECT MAX(season) FROM team_seasons WHERE team_abbr = ?", (abbr,)).fetchone()[0]


def latest_form_season(conn: sqlite3.Connection) -> str | None:
    return conn.execute("SELECT MAX(season) FROM team_game_log").fetchone()[0]


def get_form(conn: sqlite3.Connection, abbr: str, season: str) -> dict | None:
    games = conn.execute(
        """SELECT game_date, opponent_abbr, is_home, won, wins, losses, win_pct, home_win_pct, road_win_pct
           FROM team_game_log WHERE team_abbr = ? AND season = ? ORDER BY game_date, game_id""",
        (abbr, season),
    ).fetchall()
    if not games:
        return None
    last = games[-1]
    return {
        "season": season,
        "wins": last["wins"], "losses": last["losses"], "win_pct": last["win_pct"],
        "home_win_pct": last["home_win_pct"], "road_win_pct": last["road_win_pct"],
        "games": [
            {"date": g["game_date"], "opponent_abbr": g["opponent_abbr"], "is_home": bool(g["is_home"]),
             "won": bool(g["won"]), "win_pct": g["win_pct"]}
            for g in games
        ],
    }
