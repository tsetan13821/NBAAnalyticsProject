import sqlite3

from app.repositories.refs import player_columns, player_ref, team_columns, team_ref


def list_seasons(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        f"""SELECT s.season, s.champion_abbr, s.mvp_player_id,
                   {team_columns('f', 't_')}, {player_columns('p', 'p_')}
            FROM seasons s
            LEFT JOIN franchises f ON f.abbr = s.champion_abbr
            LEFT JOIN players p ON p.player_id = s.mvp_player_id
            ORDER BY s.season DESC"""
    ).fetchall()
    return [
        {
            "season": r["season"],
            "champion": team_ref(r, "t_") if r["champion_abbr"] else None,
            "mvp": player_ref(r, "p_") if r["mvp_player_id"] else None,
        }
        for r in rows
    ]


def season_exists(conn: sqlite3.Connection, season: str) -> bool:
    return conn.execute("SELECT 1 FROM seasons WHERE season = ?", (season,)).fetchone() is not None
