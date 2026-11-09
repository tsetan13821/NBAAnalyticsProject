"""Build the serving database into a temp folder and check its integrity."""
import json
import sqlite3

import pandas as pd
import pytest

from src.export_db import build_database
from src.game_model.availability import _capped
from src.game_model.predict import load_model, win_probability
from src.paths import CURRENT_SEASON_STATS, RAW_PLAYER_STATS


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    folder = tmp_path_factory.mktemp("serving")
    db_path = folder / "nba.db"
    counts = build_database(db_path=db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    yield conn, counts
    conn.close()


def scalar(conn, sql, *params):
    return conn.execute(sql, params).fetchone()[0]


def test_schema_version_and_integrity(built):
    conn, counts = built
    assert scalar(conn, "PRAGMA user_version") == 3
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert all(n > 0 for n in counts.values()), counts


def test_every_raw_player_season_is_exported(built):
    conn, _ = built
    raw = pd.concat([pd.read_csv(RAW_PLAYER_STATS), pd.read_csv(CURRENT_SEASON_STATS)])
    assert scalar(conn, "SELECT COUNT(*) FROM player_seasons") == len(raw)
    assert scalar(conn, "SELECT COUNT(*) FROM players") == raw["PLAYER_ID"].nunique()
    assert scalar(conn, "SELECT COUNT(*) FROM players WHERE position_group IS NULL") == 0


def test_season_in_progress_is_kept_out_of_the_models(built):
    conn, _ = built
    current = pd.read_csv(CURRENT_SEASON_STATS)["SEASON"].iloc[0]
    meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    assert meta["current_season"] == current
    assert meta["last_season"] < current
    assert conn.execute("SELECT season FROM seasons WHERE in_progress = 1").fetchall() == [(current,)]
    assert scalar(conn, "SELECT COUNT(*) FROM team_seasons WHERE season = ?", current) == 30
    # No MVP, archetype or similarity data for a season that hasn't finished.
    for sql in (
        "SELECT COUNT(*) FROM mvp_candidates WHERE season = ?",
        "SELECT COUNT(*) FROM player_seasons WHERE season = ? AND archetype IS NOT NULL",
        "SELECT COUNT(*) FROM similar_players WHERE season = ?",
    ):
        assert scalar(conn, sql, current) == 0, sql


def test_current_teams_come_from_rosters(built):
    conn, _ = built
    on_roster = scalar(conn, "SELECT COUNT(*) FROM players WHERE current_team_abbr IS NOT NULL")
    # About 15 players per team are on a roster; some current players debuted after the data ends.
    assert 300 <= on_roster <= 30 * 18, on_roster
    # Almost nobody whose last season in the data is long gone is on a roster (the odd comeback from
    # overseas happens: Mario Hezonja's last season here is 2019-20, and he is back on a roster).
    assert scalar(conn, """
        SELECT COUNT(*) FROM players p JOIN seasons s ON s.season = p.last_season
        WHERE p.current_team_abbr IS NOT NULL AND s.start_year < (SELECT MAX(start_year) FROM seasons) - 3
    """) <= 5
    rosters_as_of = scalar(conn, "SELECT value FROM meta WHERE key = 'rosters_as_of'")
    assert pd.Timestamp(rosters_as_of).year >= 2026


def test_mvp_tables_are_consistent(built):
    conn, _ = built
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
    conn, _ = built
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
    conn, _ = built
    assert scalar(conn, "SELECT COUNT(*) FROM similar_players WHERE player_id = similar_player_id") == 0
    assert scalar(conn, "SELECT MAX(n) FROM (SELECT COUNT(*) n FROM similar_players GROUP BY player_id, season)") == 5


def test_game_log_final_records_match_standings(built):
    conn, _ = built
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
    conn, _ = built
    bad = conn.execute("""
        SELECT season, conference, MIN(conference_rank), MAX(conference_rank), COUNT(*)
        FROM team_seasons GROUP BY season, conference
        HAVING MIN(conference_rank) != 1 OR MAX(conference_rank) > COUNT(*)
    """).fetchall()
    assert bad == []


def test_game_predictions_follow_from_their_inputs(built):
    conn, _ = built
    model = load_model()
    stored = json.loads(scalar(conn, "SELECT value FROM meta WHERE key = 'game_model'"))
    assert stored == model
    rows = conn.execute("SELECT features, pred_margin, home_win_prob FROM game_predictions").fetchall()
    assert rows
    for features, margin, prob in rows:
        inputs = json.loads(features)
        expected = model["intercept"] + sum(inputs[f] * c for f, c in model["coefficients"].items())
        assert margin == pytest.approx(expected, abs=0.01)
        assert prob == pytest.approx(float(win_probability(margin, model["spread"])), abs=1e-3)


def test_game_players_reproduce_tonights_values(built):
    """The API's what-ifs recompute a team's value from these rows, so they must add up to the stored one."""
    conn, _ = built
    games = pd.read_sql("SELECT game_id, home_abbr, away_abbr, home_tonight_value, away_tonight_value, played "
                        "FROM game_predictions", conn)
    players = pd.read_sql("SELECT * FROM game_players", conn)
    by_team = dict(iter(players.groupby(["game_id", "team_abbr"])))
    for g in games.itertuples(index=False):
        for side in ("home", "away"):
            team = by_team[(g.game_id, getattr(g, f"{side}_abbr"))]
            value = _capped(team["rate_above"].to_numpy(), team["expected_minutes"].to_numpy(), team["chance"].to_numpy())
            assert value == pytest.approx(getattr(g, f"{side}_tonight_value"), abs=0.02), (g.game_id, side)
        assert players.loc[players["game_id"] == g.game_id, "played"].isna().all() == (not g.played)
    assert players["chance"].between(0, 1).all()
    assert scalar(conn, "SELECT COUNT(*) FROM game_players WHERE status_source = 'carried' AND status IS NULL") == 0


def test_game_meta(built):
    conn, _ = built
    meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    metrics, live = json.loads(meta["game_model_metrics"]), json.loads(meta["game_live"])
    assert metrics["held_out"]["accuracy"] > metrics["baselines"]["better_record"]
    assert live["season"] == meta["current_season"]
    assert live["games_played"] == scalar(conn, "SELECT COUNT(*) FROM game_predictions WHERE played = 1")
