"""Build the serving database into a temp folder and check its integrity."""
import json
import math
import sqlite3

import joblib
import numpy as np
import pandas as pd
import pytest

from src.export_db import build_database
from src.paths import NEXT_GAME_MODEL, RAW_PLAYER_STATS


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    folder = tmp_path_factory.mktemp("serving")
    db_path, model_path = folder / "nba.db", folder / "next_game_model.json"
    counts, _ = build_database(db_path=db_path, model_path=model_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    yield conn, counts, model_path
    conn.close()


def scalar(conn, sql, *params):
    return conn.execute(sql, params).fetchone()[0]


def test_schema_version_and_integrity(built):
    conn, counts, _ = built
    assert scalar(conn, "PRAGMA user_version") == 1
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert all(n > 0 for n in counts.values()), counts


def test_every_raw_player_season_is_exported(built):
    conn, _, _ = built
    raw = pd.read_csv(RAW_PLAYER_STATS)
    assert scalar(conn, "SELECT COUNT(*) FROM player_seasons") == len(raw)
    assert scalar(conn, "SELECT COUNT(*) FROM players") == raw["PLAYER_ID"].nunique()
    assert scalar(conn, "SELECT COUNT(*) FROM players WHERE position_group IS NULL") == 0


def test_mvp_tables_are_consistent(built):
    conn, _, _ = built
    assert scalar(conn, "SELECT COUNT(*) FROM mvp_seasons") == 26
    assert scalar(conn, "SELECT SUM(correct) FROM mvp_seasons") >= 19
    # exactly one real MVP per season, ranks are 1..n, shares sum to 1
    per_season = conn.execute("""
        SELECT season, SUM(is_mvp), MIN(rank), MAX(rank), COUNT(*), SUM(score_share)
        FROM mvp_candidates GROUP BY season
    """).fetchall()
    for season, mvps, lo, hi, n, share in per_season:
        assert mvps == 1 and lo == 1 and hi == n, season
        assert share == pytest.approx(1.0, abs=1e-4), season
    # mvp_seasons agrees with mvp_candidates
    mismatches = scalar(conn, """
        SELECT COUNT(*) FROM mvp_seasons s
        JOIN mvp_candidates c ON c.season = s.season AND c.rank = 1
        WHERE c.player_id != s.predicted_player_id
    """)
    assert mismatches == 0


def test_percentiles_are_bounded_and_complete(built):
    conn, _, _ = built
    lo, hi = conn.execute("SELECT MIN(pts_pg), MAX(pts_pg) FROM player_percentiles").fetchone()
    assert 0 < lo and hi <= 100
    # each player-season has an 'ALL' row and a row for its own position group
    assert scalar(conn, "SELECT COUNT(*) FROM player_percentiles WHERE peer_group = 'ALL'") == \
        scalar(conn, "SELECT COUNT(*) FROM player_seasons")
    missing_group = scalar(conn, """
        SELECT COUNT(*) FROM player_seasons ps JOIN players p USING (player_id)
        LEFT JOIN player_percentiles pp
          ON pp.player_id = ps.player_id AND pp.season = ps.season AND pp.peer_group = p.position_group
        WHERE pp.player_id IS NULL
    """)
    assert missing_group == 0


def test_similar_players_exclude_self(built):
    conn, _, _ = built
    assert scalar(conn, "SELECT COUNT(*) FROM similar_players WHERE player_id = similar_player_id") == 0
    assert scalar(conn, "SELECT MAX(n) FROM (SELECT COUNT(*) n FROM similar_players GROUP BY player_id, season)") == 5


def test_game_log_final_records_match_standings(built):
    conn, _, _ = built
    mismatches = conn.execute("""
        WITH last_game AS (
            SELECT team_abbr, season, wins, losses,
                   ROW_NUMBER() OVER (PARTITION BY team_abbr, season ORDER BY game_date DESC, game_id DESC) AS rn
            FROM team_game_log
        )
        SELECT l.team_abbr, l.season, l.wins, l.losses, t.wins, t.losses
        FROM last_game l JOIN team_seasons t USING (team_abbr, season)
        WHERE l.rn = 1 AND (l.wins != t.wins OR l.losses != t.losses)
    """).fetchall()
    assert mismatches == []


def test_conference_ranks(built):
    conn, _, _ = built
    bad = conn.execute("""
        SELECT season, conference, MIN(conference_rank), MAX(conference_rank), COUNT(*)
        FROM team_seasons GROUP BY season, conference
        HAVING MIN(conference_rank) != 1 OR MAX(conference_rank) > COUNT(*)
    """).fetchall()
    assert bad == []


def _predict(model, features):
    margin = math.log(model["base_score"] / (1 - model["base_score"]))
    for node in model["trees"]:
        while "leaf" not in node:
            next_id = node["yes"] if features[node["split"]] < node["split_condition"] else node["no"]
            node = next(child for child in node["children"] if child["nodeid"] == next_id)
        margin += node["leaf"]
    return 1 / (1 + math.exp(-margin))


def test_exported_model_matches_xgboost(built):
    _, _, model_path = built
    model = json.loads(model_path.read_text())
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.uniform(0, 1, (500, 4)), columns=model["features"][:4])
    X["WinPCT_Diff"] = X["HOME_Overall_WinPCT"] - X["AWAY_Overall_WinPCT"]
    X["HomeAway_Diff"] = X["HOME_Home_WinPCT"] - X["AWAY_Away_WinPCT"]

    expected = joblib.load(NEXT_GAME_MODEL).predict_proba(X[model["features"]])[:, 1]
    actual = np.array([_predict(model, row) for row in X.to_dict("records")])
    assert np.abs(expected - actual).max() < 1e-5
