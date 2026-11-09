import sqlite3

from app.repositories.refs import player_columns, player_ref, team_columns, team_ref
from app.text import escape_like, normalize_search

STAT_FIELDS = (
    "games", "min_pg", "pts_pg", "reb_pg", "ast_pg", "stl_pg", "blk_pg", "tov_pg",
    "fg_pct", "fg3_pct", "ft_pct", "ts_pct", "efg_pct", "usg_pct", "pie",
    "off_rating", "def_rating", "net_rating", "ast_to", "oreb_pct", "dreb_pct", "ast_pct", "reb_pct",
)
METRIC_FIELDS = STAT_FIELDS[1:]  # everything except games

_SUMMARY_COLUMNS = (
    f"{player_columns('p', 'p_')}, p.position, p.first_season, p.last_season, "
    f"{team_columns('f', 't_')}, {team_columns('cf', 'ct_')}"
)
_SUMMARY_FROM = (
    "FROM players p JOIN franchises f ON f.abbr = p.latest_team_abbr"
    " LEFT JOIN franchises cf ON cf.abbr = p.current_team_abbr"
)
_BIO_FIELDS = (
    "height_in", "weight_lb", "country", "college", "draft_year", "draft_round", "draft_number", "seasons_played",
)
_CAREER_FIELDS = ("min_pg", "pts_pg", "reb_pg", "ast_pg", "stl_pg", "blk_pg")


def _summary(row: sqlite3.Row) -> dict:
    return {
        **player_ref(row, "p_"),
        "position": row["position"],
        "first_season": row["first_season"],
        "last_season": row["last_season"],
        "latest_team": team_ref(row, "t_"),
        "current_team": team_ref(row, "ct_") if row["ct_abbr"] else None,
    }


def search_players(
    conn: sqlite3.Connection,
    *,
    query: str | None,
    position_group: str | None,
    season: str | None,
    team: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict], int]:
    conditions, params = [], {}
    normalized = normalize_search(query) if query else ""
    if normalized:
        escaped = escape_like(normalized)
        conditions.append(r"p.search_name LIKE :contains ESCAPE '\'")
        params |= {"contains": f"%{escaped}%", "prefix": f"{escaped}%", "word_prefix": f"% {escaped}%"}
    if position_group:
        conditions.append("p.position_group = :position_group")
        params["position_group"] = position_group
    if season or team:
        conditions.append("""EXISTS (
            SELECT 1 FROM player_seasons ps WHERE ps.player_id = p.player_id
            AND (:season IS NULL OR ps.season = :season)
            AND (:team IS NULL OR ps.team_abbr = :team))""")
        params |= {"season": season, "team": team}
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Name matches at the start of the first or last name rank above matches mid-name.
    relevance = (
        r"CASE WHEN p.search_name LIKE :prefix ESCAPE '\'"
        r" OR p.search_name LIKE :word_prefix ESCAPE '\' THEN 0 ELSE 1 END,"
        if normalized else ""
    )
    rows = conn.execute(
        f"SELECT {_SUMMARY_COLUMNS} {_SUMMARY_FROM} {where}"
        f" ORDER BY {relevance} p.last_season DESC, p.name LIMIT :limit OFFSET :offset",
        params | {"limit": limit, "offset": offset},
    ).fetchall()
    total = conn.execute(f"SELECT COUNT(*) FROM players p {where}", params).fetchone()[0]
    return [_summary(row) for row in rows], total


def get_profile(conn: sqlite3.Connection, player_id: int) -> dict | None:
    row = conn.execute(
        f"SELECT {_SUMMARY_COLUMNS}, {', '.join(f'p.{c}' for c in _BIO_FIELDS)} {_SUMMARY_FROM} WHERE p.player_id = ?",
        (player_id,),
    ).fetchone()
    if row is None:
        return None

    seasons = conn.execute(
        f"""SELECT ps.season, ps.team_abbr, ps.team_abbr_then, ps.archetype, ps.tier, s.in_progress,
                   {', '.join(f'ps.{f}' for f in STAT_FIELDS)}
            FROM player_seasons ps JOIN seasons s USING (season) WHERE ps.player_id = ? ORDER BY ps.season""",
        (player_id,),
    ).fetchall()
    # Career averages are weighted by games played in each season.
    weighted = ", ".join(f"SUM({f} * games) / SUM(games) AS {f}" for f in _CAREER_FIELDS)
    career = conn.execute(
        f"SELECT SUM(games) AS games, {weighted} FROM player_seasons WHERE player_id = ?", (player_id,)
    ).fetchone()
    mvp_seasons = [r[0] for r in conn.execute(
        "SELECT season FROM seasons WHERE mvp_player_id = ? ORDER BY season", (player_id,)
    )]

    return {
        **_summary(row),
        **{field: row[field] for field in _BIO_FIELDS},
        "mvp_seasons": mvp_seasons,
        "career": {"games": career["games"], **{f: round(career[f], 2) for f in _CAREER_FIELDS}},
        "seasons": [dict(season) for season in seasons],
    }


def player_seasons_for(conn: sqlite3.Connection, player_id: int) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT season FROM player_seasons WHERE player_id = ? ORDER BY season", (player_id,)
    )]


def get_similar(conn: sqlite3.Connection, player_id: int, season: str | None) -> dict | None:
    """Similar players for a season (default: the player's latest season that has an archetype)."""
    target = conn.execute(
        f"""SELECT ps.season, ps.archetype, ps.tier, {player_columns('p', 'p_')}
            FROM player_seasons ps JOIN players p USING (player_id)
            WHERE ps.player_id = :player_id AND ps.archetype IS NOT NULL
              AND (:season IS NULL OR ps.season = :season)
            ORDER BY ps.season DESC LIMIT 1""",
        {"player_id": player_id, "season": season},
    ).fetchone()
    if target is None:
        return None

    rows = conn.execute(
        f"""SELECT s.rank, s.distance, ps.team_abbr, ps.archetype, ps.tier, ps.pts_pg, ps.reb_pg, ps.ast_pg,
                   {player_columns('p', 'p_')}
            FROM similar_players s
            JOIN player_seasons ps ON ps.player_id = s.similar_player_id AND ps.season = s.season
            JOIN players p ON p.player_id = s.similar_player_id
            WHERE s.player_id = ? AND s.season = ? ORDER BY s.rank""",
        (player_id, target["season"]),
    ).fetchall()
    return {
        "season": target["season"],
        "player": player_ref(target, "p_"),
        "archetype": target["archetype"],
        "tier": target["tier"],
        "similar": [
            {
                "rank": r["rank"], "player": player_ref(r, "p_"), "team_abbr": r["team_abbr"],
                "archetype": r["archetype"], "tier": r["tier"], "distance": r["distance"],
                "pts_pg": r["pts_pg"], "reb_pg": r["reb_pg"], "ast_pg": r["ast_pg"],
            }
            for r in rows
        ],
    }


def latest_common_season(conn: sqlite3.Connection, player_ids: list[int]) -> str | None:
    placeholders = ", ".join("?" for _ in player_ids)
    row = conn.execute(
        f"""SELECT season FROM player_seasons WHERE player_id IN ({placeholders})
            GROUP BY season HAVING COUNT(DISTINCT player_id) = ? ORDER BY season DESC LIMIT 1""",
        (*player_ids, len(set(player_ids))),
    ).fetchone()
    return row[0] if row else None


def get_comparison_rows(
    conn: sqlite3.Connection, player_ids: list[int], season: str, by_position: bool
) -> dict[int, dict]:
    """Stats and percentiles for each player in `season`, keyed by player id (missing players omitted)."""
    placeholders = ", ".join("?" for _ in player_ids)
    peer = "p.position_group" if by_position else "'ALL'"
    stat_cols = ", ".join(f"ps.{f} AS s_{f}" for f in METRIC_FIELDS)
    pct_cols = ", ".join(f"pp.{f} AS q_{f}" for f in METRIC_FIELDS)
    rows = conn.execute(
        f"""SELECT {player_columns('p', 'p_')}, ps.team_abbr, pp.peer_group, {stat_cols}, {pct_cols}
            FROM player_seasons ps
            JOIN players p USING (player_id)
            JOIN player_percentiles pp
              ON pp.player_id = ps.player_id AND pp.season = ps.season AND pp.peer_group = {peer}
            WHERE ps.season = ? AND ps.player_id IN ({placeholders})""",
        (season, *player_ids),
    ).fetchall()
    return {
        r["p_player_id"]: {
            "player": player_ref(r, "p_"),
            "team_abbr": r["team_abbr"],
            "peer_group": r["peer_group"],
            "stats": {f: r[f"s_{f}"] for f in METRIC_FIELDS},
            "percentiles": {f: r[f"q_{f}"] for f in METRIC_FIELDS},
        }
        for r in rows
    }
