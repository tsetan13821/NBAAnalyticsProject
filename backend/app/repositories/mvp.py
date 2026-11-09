import sqlite3

from app.repositories.refs import player_columns, player_ref, team_columns, team_ref

ERA_LABELS = {1: "2000-01 to 2007-08", 2: "2008-09 onward"}


def get_overview(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        f"""SELECT m.season, m.era, m.actual_rank, m.correct, m.candidates,
                   {player_columns('pred', 'pr_')}, {player_columns('act', 'ac_')}
            FROM mvp_seasons m
            JOIN players pred ON pred.player_id = m.predicted_player_id
            JOIN players act ON act.player_id = m.actual_player_id
            ORDER BY m.season"""
    ).fetchall()
    seasons = [
        {
            "season": r["season"], "era": r["era"], "actual_rank": r["actual_rank"],
            "correct": bool(r["correct"]), "candidates": r["candidates"],
            "predicted": player_ref(r, "pr_"), "actual": player_ref(r, "ac_"),
        }
        for r in rows
    ]
    eras = [
        {
            "era": era, "label": label,
            "seasons": sum(1 for s in seasons if s["era"] == era),
            "correct": sum(1 for s in seasons if s["era"] == era and s["correct"]),
        }
        for era, label in ERA_LABELS.items()
    ]
    return {
        "correct": sum(s["correct"] for s in seasons),
        "total": len(seasons),
        "top3": sum(1 for s in seasons if s["actual_rank"] <= 3),
        "eras": eras,
        "seasons": seasons,
    }


def get_race(conn: sqlite3.Connection, season: str, limit: int) -> dict | None:
    summary = conn.execute(
        "SELECT era, correct, actual_rank FROM mvp_seasons WHERE season = ?", (season,)
    ).fetchone()
    if summary is None:
        return None

    rows = conn.execute(
        f"""SELECT c.rank, c.model_score, c.score_share, c.is_mvp,
                   ps.games, ps.pts_pg, ps.reb_pg, ps.ast_pg, ps.ts_pct, ps.pie,
                   ts.win_pct, ts.conference_rank,
                   {player_columns('p', 'p_')}, {team_columns('f', 't_')}
            FROM mvp_candidates c
            JOIN players p ON p.player_id = c.player_id
            JOIN player_seasons ps ON ps.player_id = c.player_id AND ps.season = c.season
            JOIN team_seasons ts ON ts.team_abbr = ps.team_abbr AND ts.season = ps.season
            JOIN franchises f ON f.abbr = ps.team_abbr
            WHERE c.season = ? ORDER BY c.rank LIMIT ?""",
        (season, limit),
    ).fetchall()
    return {
        "season": season,
        "era": summary["era"],
        "correct": bool(summary["correct"]),
        "actual_rank": summary["actual_rank"],
        "candidates": [
            {
                "rank": r["rank"], "player": player_ref(r, "p_"), "team": team_ref(r, "t_"),
                "model_score": r["model_score"], "score_share": r["score_share"], "is_mvp": bool(r["is_mvp"]),
                "stats": {k: r[k] for k in ("games", "pts_pg", "reb_pg", "ast_pg", "ts_pct", "pie")},
                "team_win_pct": r["win_pct"], "team_conference_rank": r["conference_rank"],
            }
            for r in rows
        ],
    }
