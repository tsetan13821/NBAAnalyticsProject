import pandas as pd
import numpy as np
import os
import time
from nba_api.stats.endpoints import leaguegamefinder
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

def fetch_and_process_game_data(seasons=['2021-22', '2022-23', '2023-24']):
    print(f"Fetching game data for seasons: {seasons}...")
    
    all_games_list = []
    
    for season in seasons:
        gamefinder = leaguegamefinder.LeagueGameFinder(season_nullable=season, league_id_nullable='00')
        games = gamefinder.get_data_frames()[0]
        
        # Filter regular season games only
        games = games[games['SEASON_ID'].str.contains('220')]
        
        all_games_list.append(games)
        time.sleep(1) # sleep to prevent rate limiting
        
    df = pd.concat(all_games_list, ignore_index=True)
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df.sort_values(by='GAME_DATE')
    
    # Identify Home and Away games based on matchup string (e.g. "LAL vs. BOS" vs "LAL @ BOS")
    df['HOME_GAME'] = df['MATCHUP'].str.contains(' vs. ')
    
    # We'll split records to home and away
    home_games = df[df['HOME_GAME']].copy()
    away_games = df[~df['HOME_GAME']].copy()
    
    home_games = home_games[['GAME_ID', 'GAME_DATE', 'TEAM_ID', 'TEAM_ABBREVIATION', 'WL', 'SEASON_ID']].rename(
        columns={'TEAM_ID': 'HOME_TEAM_ID', 'TEAM_ABBREVIATION': 'HOME_TEAM_ABBREVIATION', 'WL': 'HOME_WL'}
    )
    
    away_games = away_games[['GAME_ID', 'TEAM_ID', 'TEAM_ABBREVIATION']].rename(
        columns={'TEAM_ID': 'AWAY_TEAM_ID', 'TEAM_ABBREVIATION': 'AWAY_TEAM_ABBREVIATION'}
    )
    
    # Merge home and away data to create a single game record dataset
    games_merged = pd.merge(home_games, away_games, on='GAME_ID')
    games_merged['HOME_WIN'] = np.where(games_merged['HOME_WL'] == 'W', 1, 0)
    
    # Now, we need tracking of team records up to the GAME_DATE
    # We will simulate overall win%, home win%, away win%
    print("Calculating running win percentages...")
    
    games_merged['HOME_Overall_WinPCT'] = 0.5
    games_merged['HOME_Home_WinPCT'] = 0.5
    games_merged['AWAY_Overall_WinPCT'] = 0.5
    games_merged['AWAY_Away_WinPCT'] = 0.5
    
    # To keep it simple and relatively fast but robust, we'll iterate through seasons and teams
    season_records = {} # {season_id: {team_id: {'W': 0, 'L': 0, 'Home_W': 0, 'Home_L': 0, 'Away_W': 0, 'Away_L': 0}}}
    
    enriched_rows = []
    
    for idx, row in games_merged.iterrows():
        season = row['SEASON_ID']
        home_team = row['HOME_TEAM_ID']
        away_team = row['AWAY_TEAM_ID']
        
        if season not in season_records:
            season_records[season] = {}
            
        if home_team not in season_records[season]:
            season_records[season][home_team] = {'W': 0, 'L': 0, 'Home_W': 0, 'Home_L': 0, 'Away_W': 0, 'Away_L': 0}
            
        if away_team not in season_records[season]:
            season_records[season][away_team] = {'W': 0, 'L': 0, 'Home_W': 0, 'Home_L': 0, 'Away_W': 0, 'Away_L': 0}
            
        # Get historical records before updating BEFORE THIS GAME
        ht_req = season_records[season][home_team]
        at_req = season_records[season][away_team]
        
        # Calculate win percentages (default to 0.5 if no games played yet)
        h_overall_g = ht_req['W'] + ht_req['L']
        row['HOME_Overall_WinPCT'] = ht_req['W'] / h_overall_g if h_overall_g > 0 else 0.5
        
        h_home_g = ht_req['Home_W'] + ht_req['Home_L']
        row['HOME_Home_WinPCT'] = ht_req['Home_W'] / h_home_g if h_home_g > 0 else 0.5
        
        a_overall_g = at_req['W'] + at_req['L']
        row['AWAY_Overall_WinPCT'] = at_req['W'] / a_overall_g if a_overall_g > 0 else 0.5
        
        a_away_g = at_req['Away_W'] + at_req['Away_L']
        row['AWAY_Away_WinPCT'] = at_req['Away_W'] / a_away_g if a_away_g > 0 else 0.5
        
        # Now update the records
        if row['HOME_WIN'] == 1:
            ht_req['W'] += 1
            ht_req['Home_W'] += 1
            at_req['L'] += 1
            at_req['Away_L'] += 1
        else:
            ht_req['L'] += 1
            ht_req['Home_L'] += 1
            at_req['W'] += 1
            at_req['Away_W'] += 1
            
        enriched_rows.append(row)
        
    final_df = pd.DataFrame(enriched_rows)
    return final_df


def train_next_game_model():
    # Attempt to load data if exists, otherwise fetch
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_path = os.path.join(base_dir, 'data', 'processed', 'game_matchups.csv')
    
    if os.path.exists(data_path):
        print("Loading cached game matchup data...")
        df = pd.read_csv(data_path)
    else:
        df = fetch_and_process_game_data(seasons=['2020-21', '2021-22', '2022-23', '2023-24'])
        df.to_csv(data_path, index=False)
        print(f"Game matchups saved to {data_path}")

    # Exclude the first 10 games of the season for each team because stats are too noisy early on
    # A simple proxy is keeping games from November onwards, but our dataset has running stats
    # Also drop first few weeks if needed. For now, training on everything
    
    features = ['HOME_Overall_WinPCT', 'HOME_Home_WinPCT', 'AWAY_Overall_WinPCT', 'AWAY_Away_WinPCT']
    
    # Calculate differentials which helps XGBoost
    df['WinPCT_Diff'] = df['HOME_Overall_WinPCT'] - df['AWAY_Overall_WinPCT']
    df['HomeAway_Diff'] = df['HOME_Home_WinPCT'] - df['AWAY_Away_WinPCT']
    
    features.extend(['WinPCT_Diff', 'HomeAway_Diff'])
    
    # We can also drop the exact 0.5 initialization values as they represent 0 games played
    valid_games = df[(df['HOME_Overall_WinPCT'] != 0.5) | (df['AWAY_Overall_WinPCT'] != 0.5)]

    X = valid_games[features]
    y = valid_games['HOME_WIN']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=True)
    
    print("Training XGBoost Classifier...")
    model = XGBClassifier(
        n_estimators=100, 
        learning_rate=0.1, 
        max_depth=4,
        random_state=42,
        eval_metric='logloss'
    )
    
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model Accuracy on Test Set: {accuracy * 100:.2f}%")
    print(classification_report(y_test, y_pred))
    
    # Save Model
    model_dir = os.path.join(base_dir, 'saved_models')
    os.makedirs(model_dir, exist_ok=True)
    
    model_path = os.path.join(model_dir, 'next_game_model.pkl')
    joblib.dump(model, model_path)
    print(f"Model saved to {model_path}")
    
    return model

if __name__ == "__main__":
    train_next_game_model()
