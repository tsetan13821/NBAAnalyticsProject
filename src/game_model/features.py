"""The model's inputs: one row per game, each feature the home side minus the away side.

    python -m src.game_model.features     # writes data/processed/game_features.csv.gz

Feature groups (the evaluation adds them one group at a time to show what each is worth):
    strength      ELO_DIFF            Elo gap before the game, in points of expected margin
    home          NO_CROWD, REDUCED_CROWD
                                      the model's intercept is the home edge; these flag games with
                                      no home crowd (bubble, neutral site) or a reduced one (2020-21)
    season        NET_DIFF, FORM_DIFF net rating so far and recent form, per 100 possessions
    schedule      REST_DIFF, {HOME,AWAY}_B2B, {HOME,AWAY}_3IN4, AWAY_TRAVEL, AWAY_TZ_EAST
    roster        FULL_DIFF           value of each roster at full strength
                  RECENT_DIFF         value of the lineups each team has actually fielded lately
    availability  AVAIL_DIFF          value available tonight minus what each team has recently fielded

AVAIL_ACTUAL_DIFF is the same as AVAIL_DIFF but from who really played. It is never a model input
(nobody knows it before the game); the evaluation uses it to show how much the uncertainty of the
injury report costs.
"""
import pandas as pd

from src.game_model.availability import (
    DEFAULT_PLAY_RATES,
    load_injuries,
    load_player_games,
    measured_play_rates,
    team_availability,
)
from src.game_model.games import ELO_PER_POINT, build_games
from src.game_model.seasons import configured_seasons
from src.paths import GAME_FEATURES

FEATURE_GROUPS: dict[str, list[str]] = {
    'strength': ['ELO_DIFF'],
    'home': ['NO_CROWD', 'REDUCED_CROWD'],
    'season': ['NET_DIFF', 'FORM_DIFF'],
    'schedule': ['REST_DIFF', 'HOME_B2B', 'AWAY_B2B', 'HOME_3IN4', 'AWAY_3IN4', 'AWAY_TRAVEL', 'AWAY_TZ_EAST'],
    'roster': ['FULL_DIFF', 'RECENT_DIFF'],
    'availability': ['AVAIL_DIFF'],
}
FEATURES = [f for group in FEATURE_GROUPS.values() for f in group]


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Differences and flags from the per-side columns of games + availability."""
    out = df.copy()
    out['ELO_DIFF'] = (out['HOME_ELO'] - out['AWAY_ELO']) / ELO_PER_POINT
    out['NO_CROWD'] = (out['BUBBLE'] | out['NEUTRAL_SITE']).astype(int)
    out['REDUCED_CROWD'] = (out['REDUCED_CROWD'] & ~out['NO_CROWD'].astype(bool)).astype(int)
    out['NET_DIFF'] = out['HOME_NET'] - out['AWAY_NET']
    out['FORM_DIFF'] = out['HOME_FORM'] - out['AWAY_FORM']
    out['REST_DIFF'] = out['HOME_REST'] - out['AWAY_REST']
    out['AWAY_TRAVEL'] = out['AWAY_TRAVEL_KM'] / 1000
    out['AWAY_TZ_EAST'] = out['AWAY_TZ_SHIFT'].clip(lower=0)
    out['FULL_DIFF'] = out['HOME_FULL_VALUE'] - out['AWAY_FULL_VALUE']
    out['RECENT_DIFF'] = out['HOME_RECENT_VALUE'] - out['AWAY_RECENT_VALUE']
    home_change = out['HOME_TONIGHT_VALUE'] - out['HOME_RECENT_VALUE']
    away_change = out['AWAY_TONIGHT_VALUE'] - out['AWAY_RECENT_VALUE']
    out['AVAIL_DIFF'] = home_change - away_change
    out['AVAIL_ACTUAL_DIFF'] = (out['HOME_ACTUAL_VALUE'] - out['HOME_RECENT_VALUE']) - (
        out['AWAY_ACTUAL_VALUE'] - out['AWAY_RECENT_VALUE'])
    return out


def build_features() -> tuple[pd.DataFrame, dict[str, float]]:
    """Every game with player data, its features and outcome; plus the measured injury-status play rates."""
    seasons = configured_seasons()
    games = build_games(seasons.team)
    games = games[games['SEASON'].isin(seasons.player)].reset_index(drop=True)
    player_games = load_player_games(seasons.player)
    injuries = load_injuries(seasons.injury)

    # Measure how often players listed with each status went on to play, in completed training
    # seasons only (never the held-out season or the one in progress), then use those rates.
    train_seasons = [s for s in seasons.injury if s < seasons.completed]
    _, per_player = team_availability(games, player_games, injuries, DEFAULT_PLAY_RATES)
    in_train = per_player['GAME_ID'].isin(games.loc[games['SEASON'].isin(train_seasons), 'GAME_ID'])
    play_rates = measured_play_rates(per_player[in_train])

    per_game, _ = team_availability(games, player_games, injuries, play_rates)
    df = add_features(games.merge(per_game, on='GAME_ID'))
    df['HAS_INJURY_REPORT'] = df['SEASON'].isin(seasons.injury)
    return df, play_rates


def main():
    df, play_rates = build_features()
    df.to_csv(GAME_FEATURES, index=False, compression='gzip')
    print(f"Saved {len(df):,} games to {GAME_FEATURES}")
    print("Measured chance of playing by injury-report status:", play_rates)


if __name__ == "__main__":
    main()
