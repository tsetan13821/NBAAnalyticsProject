import argparse
import time

import joblib
import numpy as np
import pandas as pd
import yaml
from nba_api.stats.endpoints import leaguegamefinder
from sklearn.metrics import accuracy_score, classification_report
from xgboost import XGBClassifier

from src.paths import CONFIG_PATH, GAME_MATCHUPS, MODELS_DIR, NEXT_GAME_MODEL

BASE_FEATURES = ['HOME_Overall_WinPCT', 'HOME_Home_WinPCT', 'AWAY_Overall_WinPCT', 'AWAY_Away_WinPCT']
FEATURES = BASE_FEATURES + ['WinPCT_Diff', 'HomeAway_Diff']


def load_next_game_config():
    with open(CONFIG_PATH, 'r') as file:
        return yaml.safe_load(file)['next_game']


def _empty_record():
    return {'W': 0, 'L': 0, 'Home_W': 0, 'Home_L': 0, 'Away_W': 0, 'Away_L': 0}


def _pct(wins, losses):
    games = wins + losses
    return wins / games if games > 0 else 0.5


def fetch_and_process_game_data(seasons):
    print(f"Fetching game data for seasons: {seasons}...")

    all_games_list = []
    for season in seasons:
        gamefinder = leaguegamefinder.LeagueGameFinder(season_nullable=season, league_id_nullable='00', timeout=60)
        games = gamefinder.get_data_frames()[0]
        # SEASON_ID prefix 2 = regular season (1 = preseason, 3 = All-Star, 4 = playoffs)
        games = games[games['SEASON_ID'].astype(str).str.startswith('2')]
        all_games_list.append(games)
        time.sleep(1)  # Avoid NBA API rate limiting

    df = pd.concat(all_games_list, ignore_index=True)
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])

    # "LAL vs. BOS" -> LAL is home; "LAL @ BOS" -> BOS is home. Derive the home team from the
    # matchup text rather than the row's own wording: for neutral-site games (international
    # games, NBA Cup in Las Vegas) the API gives BOTH teams' rows the same "X @ Y" string.
    home_abbr = np.where(
        df['MATCHUP'].str.contains(' vs. '),
        df['MATCHUP'].str.split(' vs. ').str[0],
        df['MATCHUP'].str.split(' @ ').str[-1],
    )
    df['HOME_GAME'] = df['TEAM_ABBREVIATION'] == home_abbr

    home_games = df[df['HOME_GAME']][['GAME_ID', 'GAME_DATE', 'TEAM_ID', 'TEAM_ABBREVIATION', 'WL', 'SEASON_ID']].rename(
        columns={'TEAM_ID': 'HOME_TEAM_ID', 'TEAM_ABBREVIATION': 'HOME_TEAM_ABBREVIATION', 'WL': 'HOME_WL'}
    )
    away_games = df[~df['HOME_GAME']][['GAME_ID', 'TEAM_ID', 'TEAM_ABBREVIATION']].rename(
        columns={'TEAM_ID': 'AWAY_TEAM_ID', 'TEAM_ABBREVIATION': 'AWAY_TEAM_ABBREVIATION'}
    )

    games = pd.merge(home_games, away_games, on='GAME_ID')
    games = games.sort_values(by=['GAME_DATE', 'GAME_ID']).reset_index(drop=True)
    games['HOME_WIN'] = np.where(games['HOME_WL'] == 'W', 1, 0)

    print("Calculating running win percentages...")
    return add_running_records(games)


def add_running_records(games):
    """Add each team's season-to-date records using only games played BEFORE each game (no look-ahead).

    Expects one row per game in chronological order with SEASON_ID, HOME_TEAM_ID, AWAY_TEAM_ID, HOME_WIN.
    """
    games = games.copy()
    season_records = {}
    computed = {col: [] for col in BASE_FEATURES + ['HOME_GP_BEFORE', 'AWAY_GP_BEFORE']}

    for season, home_team, away_team, home_win in games[['SEASON_ID', 'HOME_TEAM_ID', 'AWAY_TEAM_ID', 'HOME_WIN']].itertuples(index=False):
        records = season_records.setdefault(season, {})
        home = records.setdefault(home_team, _empty_record())
        away = records.setdefault(away_team, _empty_record())

        computed['HOME_Overall_WinPCT'].append(_pct(home['W'], home['L']))
        computed['HOME_Home_WinPCT'].append(_pct(home['Home_W'], home['Home_L']))
        computed['AWAY_Overall_WinPCT'].append(_pct(away['W'], away['L']))
        computed['AWAY_Away_WinPCT'].append(_pct(away['Away_W'], away['Away_L']))
        computed['HOME_GP_BEFORE'].append(home['W'] + home['L'])
        computed['AWAY_GP_BEFORE'].append(away['W'] + away['L'])

        if home_win == 1:
            home['W'] += 1; home['Home_W'] += 1
            away['L'] += 1; away['Away_L'] += 1
        else:
            home['L'] += 1; home['Home_L'] += 1
            away['W'] += 1; away['Away_W'] += 1

    for col, values in computed.items():
        games[col] = values
    return games


def add_diff_features(df):
    df['WinPCT_Diff'] = df['HOME_Overall_WinPCT'] - df['AWAY_Overall_WinPCT']
    df['HomeAway_Diff'] = df['HOME_Home_WinPCT'] - df['AWAY_Away_WinPCT']
    return df


def train_next_game_model(refresh=False):
    config = load_next_game_config()
    seasons = config['seasons']

    if GAME_MATCHUPS.exists() and not refresh:
        print(f"Loading cached game matchup data from {GAME_MATCHUPS} (use --refresh to re-fetch)...")
        df = pd.read_csv(GAME_MATCHUPS)
    else:
        df = fetch_and_process_game_data(seasons)
        df.to_csv(GAME_MATCHUPS, index=False)
        print(f"Game matchups saved to {GAME_MATCHUPS}")

    df = add_diff_features(df)

    # Early-season records are too noisy to be informative
    min_games = config.get('min_games_before', 10)
    valid = df[(df['HOME_GP_BEFORE'] >= min_games) & (df['AWAY_GP_BEFORE'] >= min_games)]

    # Time-based split: train on earlier seasons, test on the most recent one.
    test_season_id = valid['SEASON_ID'].max()
    train, test = valid[valid['SEASON_ID'] != test_season_id], valid[valid['SEASON_ID'] == test_season_id]
    print(f"Training on {len(train)} games, testing on {len(test)} games from season id {test_season_id}")

    model = XGBClassifier(n_estimators=100, learning_rate=0.1, max_depth=4, random_state=42, eval_metric='logloss')
    model.fit(train[FEATURES], train['HOME_WIN'])

    y_pred = model.predict(test[FEATURES])
    accuracy = accuracy_score(test['HOME_WIN'], y_pred)
    home_baseline = test['HOME_WIN'].mean()
    record_baseline = accuracy_score(test['HOME_WIN'], (test['WinPCT_Diff'] >= 0).astype(int))

    print(f"Model accuracy on held-out season:      {accuracy * 100:.2f}%")
    print(f"Baseline - always pick home team:       {home_baseline * 100:.2f}%")
    print(f"Baseline - pick team with better record: {record_baseline * 100:.2f}%")
    print(classification_report(test['HOME_WIN'], y_pred))

    # Refit on all valid games for the deployed model
    model.fit(valid[FEATURES], valid['HOME_WIN'])
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, NEXT_GAME_MODEL)
    print(f"Model saved to {NEXT_GAME_MODEL}")

    return {'accuracy': accuracy, 'home_baseline': home_baseline, 'record_baseline': record_baseline}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the next-game outcome model.")
    parser.add_argument('--refresh', action='store_true', help="Re-fetch game data from the NBA API instead of using the cached CSV.")
    train_next_game_model(refresh=parser.parse_args().refresh)
