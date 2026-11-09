import sqlite3
from typing import Literal

from app.errors import NotFoundError
from app.repositories import players as players_repo

# Display metadata for every comparable metric, in the order the frontend should show them.
METRICS = [
    {"key": "pts_pg", "label": "Points", "format": "per_game", "higher_is_better": True},
    {"key": "reb_pg", "label": "Rebounds", "format": "per_game", "higher_is_better": True},
    {"key": "ast_pg", "label": "Assists", "format": "per_game", "higher_is_better": True},
    {"key": "stl_pg", "label": "Steals", "format": "per_game", "higher_is_better": True},
    {"key": "blk_pg", "label": "Blocks", "format": "per_game", "higher_is_better": True},
    {"key": "tov_pg", "label": "Turnovers", "format": "per_game", "higher_is_better": False},
    {"key": "min_pg", "label": "Minutes", "format": "per_game", "higher_is_better": True},
    {"key": "fg_pct", "label": "Field Goal %", "format": "percent", "higher_is_better": True},
    {"key": "fg3_pct", "label": "3-Point %", "format": "percent", "higher_is_better": True},
    {"key": "ft_pct", "label": "Free Throw %", "format": "percent", "higher_is_better": True},
    {"key": "ts_pct", "label": "True Shooting %", "format": "percent", "higher_is_better": True},
    {"key": "efg_pct", "label": "Effective FG %", "format": "percent", "higher_is_better": True},
    {"key": "usg_pct", "label": "Usage %", "format": "percent", "higher_is_better": True},
    {"key": "pie", "label": "Player Impact Estimate", "format": "percent", "higher_is_better": True},
    {"key": "ast_pct", "label": "Assist %", "format": "percent", "higher_is_better": True},
    {"key": "reb_pct", "label": "Rebound %", "format": "percent", "higher_is_better": True},
    {"key": "oreb_pct", "label": "Offensive Rebound %", "format": "percent", "higher_is_better": True},
    {"key": "dreb_pct", "label": "Defensive Rebound %", "format": "percent", "higher_is_better": True},
    {"key": "ast_to", "label": "Assist/Turnover", "format": "ratio", "higher_is_better": True},
    {"key": "off_rating", "label": "Offensive Rating", "format": "rating", "higher_is_better": True},
    {"key": "def_rating", "label": "Defensive Rating", "format": "rating", "higher_is_better": False},
    {"key": "net_rating", "label": "Net Rating", "format": "rating", "higher_is_better": True},
]  # tests/test_players.py checks this stays in sync with players_repo.METRIC_FIELDS


def compare_players(
    conn: sqlite3.Connection,
    player_ids: list[int],
    season: str | None,
    peer_group: Literal["ALL", "POSITION"],
) -> dict:
    ids = list(dict.fromkeys(player_ids))  # de-duplicate, keep order
    if season is None:
        season = players_repo.latest_common_season(conn, ids)
        if season is None:
            raise NotFoundError("These players never played in the same season")

    rows = players_repo.get_comparison_rows(conn, ids, season, by_position=peer_group == "POSITION")
    missing = [player_id for player_id in ids if player_id not in rows]
    if missing:
        raise NotFoundError(f"No {season} stats for player(s): {', '.join(map(str, missing))}")

    return {
        "season": season,
        "peer_group": peer_group,
        "metrics": METRICS,
        "players": [rows[player_id] for player_id in ids],
    }
