"""Unit tests for shared helpers and integrity checks on the committed datasets."""
import pandas as pd
import pytest

from src.data_collection import generate_seasons
from src.features import infer_career_positions, to_per_game
from src.nba_reference import (
    CHAMPIONS,
    MVP_WINNERS,
    franchise_abbreviation,
    get_conference,
    normalize_name,
    previous_season,
)
from src.paths import GAME_MATCHUPS, MVP_DATA, RAW_PLAYER_STATS


# --- helpers -----------------------------------------------------------------

def test_generate_seasons_crosses_century():
    assert generate_seasons("1998-99", "2001-02") == ["1998-99", "1999-00", "2000-01", "2001-02"]


@pytest.mark.parametrize("season, expected", [("2010-11", "2009-10"), ("2000-01", "1999-00"), ("2009-10", "2008-09")])
def test_previous_season(season, expected):
    assert previous_season(season) == expected


def test_normalize_name_strips_accents():
    assert normalize_name(" Nikola Jokić ") == "Nikola Jokic"
    assert normalize_name("Luka Dončić") == "Luka Doncic"


@pytest.mark.parametrize("abbr, franchise", [("SEA", "OKC"), ("NJN", "BKN"), ("NOK", "NOP"), ("VAN", "MEM"), ("LAL", "LAL")])
def test_franchise_abbreviation(abbr, franchise):
    assert franchise_abbreviation(abbr) == franchise


def test_get_conference_handles_history():
    assert get_conference("SEA") == "West"
    assert get_conference("NJN") == "East"
    assert get_conference("NOH", "2003-04") == "East"   # Hornets' first New Orleans seasons
    assert get_conference("NOH", "2010-11") == "West"
    assert get_conference("XXX") == "Unknown"


def test_to_per_game_divides_counting_stats_only():
    df = pd.DataFrame({"GP": [10, 0], "PTS": [250, 5], "MIN": [300.0, 12.0], "TS_PCT": [0.6, 0.5]})
    out = to_per_game(df)
    assert out["PTS"].tolist() == [25.0, 5.0]       # GP of 0 is treated as 1
    assert out["MIN"].tolist() == [30.0, 12.0]
    assert out["TS_PCT"].tolist() == [0.6, 0.5]     # rates are untouched
    assert df["PTS"].tolist() == [250, 5]           # input not mutated


def test_infer_career_positions():
    totals = pd.DataFrame({
        "PLAYER_ID": [1, 1, 2, 3],
        "GP":  [50, 50, 80, 80],
        "REB": [600, 500, 200, 300],
        "AST": [100, 100, 640, 160],
        "BLK": [100, 100, 10, 20],
    })
    positions = infer_career_positions(totals)
    assert positions[1] == "Center (C)"       # 11 RPG, 2 BPG
    assert positions[2] == "Point Guard (PG)"  # 8 APG
    assert positions[3] == "Shooting Guard (SG)"


# --- committed data integrity -------------------------------------------------

@pytest.fixture(scope="module")
def mvp_data():
    return pd.read_csv(MVP_DATA)


def test_mvp_data_keeps_every_raw_player_season(mvp_data):
    raw = pd.read_csv(RAW_PLAYER_STATS)
    assert len(mvp_data) == len(raw)
    assert mvp_data["WINS"].notna().all()


def test_mvp_data_has_one_mvp_per_season(mvp_data):
    per_season = mvp_data.groupby("SEASON")["IS_MVP"].sum()
    assert (per_season == 1).all(), per_season[per_season != 1]
    labelled = mvp_data[mvp_data["IS_MVP"] == 1].set_index("SEASON")["PLAYER_NAME"]
    for season, player in labelled.items():
        assert MVP_WINNERS[season] == player


def test_every_champion_exists_in_standings(mvp_data):
    team_seasons = set(zip(mvp_data["SEASON"], mvp_data["FRANCHISE_ABBREVIATION"]))
    for season, team in CHAMPIONS.items():
        assert (season, team) in team_seasons, (season, team)


def test_game_matchups_are_complete_and_unique():
    games = pd.read_csv(GAME_MATCHUPS)
    assert not games["GAME_ID"].duplicated().any()
    for season_id, season_games in games.groupby("SEASON_ID"):
        team_games = pd.concat([season_games["HOME_TEAM_ABBREVIATION"], season_games["AWAY_TEAM_ABBREVIATION"]]).value_counts()
        assert len(team_games) == 30, season_id
        assert team_games.nunique() == 1, f"uneven schedule in {season_id}: {team_games.unique()}"
