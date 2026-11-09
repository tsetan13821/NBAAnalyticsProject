"""SQL column lists and row mappers for the team/player references embedded in many responses."""
import sqlite3

from app.urls import headshot_url, logo_url


def team_columns(alias: str, prefix: str) -> str:
    """Columns needed for a TeamRef from `franchises` aliased as `alias`."""
    return ", ".join(
        f"{alias}.{col} AS {prefix}{col}"
        for col in ("abbr", "name", "primary_color", "secondary_color", "nba_team_id")
    )


def player_columns(alias: str, prefix: str) -> str:
    """Columns needed for a PlayerRef from `players` aliased as `alias`."""
    return ", ".join(f"{alias}.{col} AS {prefix}{col}" for col in ("player_id", "name", "position_group"))


def team_ref(row: sqlite3.Row, prefix: str) -> dict:
    return {
        "abbr": row[f"{prefix}abbr"],
        "name": row[f"{prefix}name"],
        "primary_color": row[f"{prefix}primary_color"],
        "secondary_color": row[f"{prefix}secondary_color"],
        "logo_url": logo_url(row[f"{prefix}nba_team_id"]),
    }


def player_ref(row: sqlite3.Row, prefix: str) -> dict:
    player_id = row[f"{prefix}player_id"]
    return {
        "id": player_id,
        "name": row[f"{prefix}name"],
        "position_group": row[f"{prefix}position_group"],
        "headshot_url": headshot_url(player_id),
    }
