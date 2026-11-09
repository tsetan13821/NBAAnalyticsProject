"""Tests for model logic plus regression guards on the committed model outputs."""
import pandas as pd
import pytest

from src.models.all_star_prediction import assign_pos
from src.models.mvp_prediction import apply_mvp_candidate_filters, run_loocv
from src.models.next_game_prediction import add_running_records
from src.paths import ALL_STARS_MASTER, CLUSTERED_PLAYERS, MVP_DATA


# --- All-Star ------------------------------------------------------------------

@pytest.mark.parametrize("name, expected", [("Nikola Jokić", "C"), ("Nikola Jokic", "C"), ("Luka Dončić", "G")])
def test_position_overrides_ignore_accents(name, expected):
    # Box-score profile alone would suggest a different position
    row = {"PLAYER_NAME": name, "GP": 70, "AST": 700, "REB": 350, "BLK": 30}
    assert assign_pos(row) == expected


def test_all_star_rosters_have_fifteen_per_conference():
    all_stars = pd.read_csv(ALL_STARS_MASTER)
    sizes = all_stars.groupby(["SEASON", "Conference"]).size()
    assert set(all_stars["Conference"]) == {"East", "West"}
    assert (sizes <= 15).all()
    assert (sizes >= 14).mean() == 1.0


# --- MVP -----------------------------------------------------------------------

def test_candidate_filters_keep_every_actual_mvp():
    candidates = apply_mvp_candidate_filters(pd.read_csv(MVP_DATA))
    assert candidates["IS_MVP"].sum() == pd.read_csv(MVP_DATA)["IS_MVP"].sum()


def test_mvp_loocv_accuracy_does_not_regress():
    results = run_loocv()
    correct = sum(r["CORRECT"] for r in results["results"])
    assert len(results["results"]) == 26
    assert correct >= 19, results["accuracy_str"]


# --- Clustering ------------------------------------------------------------------

def test_cluster_tiers_are_ordered_and_filters_applied():
    df = pd.read_csv(CLUSTERED_PLAYERS)
    assert (df["MIN"] >= 15).all(), "MIN should be per game and filtered at 15"
    for cluster, group in df.groupby("Cluster"):
        means = group.groupby("Tier")[f"{cluster}_Score"].mean()
        assert means["Elite"] > means["Very Good"] > means["Average"], cluster


# --- Next game ---------------------------------------------------------------------

def test_running_records_use_only_prior_games():
    games = pd.DataFrame({
        "SEASON_ID":    [22025, 22025, 22025, 22026],
        "HOME_TEAM_ID": [1, 2, 1, 1],
        "AWAY_TEAM_ID": [2, 1, 2, 2],
        "HOME_WIN":     [1, 1, 0, 1],
    })
    out = add_running_records(games)

    # Game 1: nobody has played yet
    assert out.loc[0, ["HOME_Overall_WinPCT", "AWAY_Overall_WinPCT", "HOME_GP_BEFORE"]].tolist() == [0.5, 0.5, 0]
    # Game 2: team 2 (home) lost game 1, team 1 (away) won it; team 1 has no road games yet
    assert out.loc[1, "HOME_Overall_WinPCT"] == 0.0
    assert out.loc[1, "AWAY_Overall_WinPCT"] == 1.0
    assert out.loc[1, "AWAY_Away_WinPCT"] == 0.5
    # Game 3: team 1 is 1-1 overall, 1-0 at home
    assert out.loc[2, "HOME_Overall_WinPCT"] == 0.5
    assert out.loc[2, "HOME_Home_WinPCT"] == 1.0
    # New season resets records
    assert out.loc[3, "HOME_GP_BEFORE"] == 0
