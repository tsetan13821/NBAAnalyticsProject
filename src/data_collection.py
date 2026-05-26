import os
import time
import yaml
import pandas as pd
from tqdm import tqdm
from nba_api.stats.endpoints import leaguedashplayerstats

def load_config(config_path="config/config.yaml"):
    with open(config_path, "r") as file:
        return yaml.safe_load(file)

def generate_seasons(start_season, end_season):
    """
    Generates a list of season strings (e.g., '2000-01', '2001-02') 
    between start_season and end_season inclusive.
    """
    start_year = int(start_season.split('-')[0])
    end_year = int(end_season.split('-')[0])
    
    seasons = []
    for year in range(start_year, end_year + 1):
        next_year_short = str(year + 1)[-2:]
        seasons.append(f"{year}-{next_year_short}")
    return seasons

def fetch_season_data(season, season_type):
    """
    Fetches Base and Advanced stats for a given season and merges them.
    """
    try:
        # Fetch Base stats
        base_stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            season_type_all_star=season_type,
            measure_type_detailed_defense='Base'
        ).get_data_frames()[0]
        
        time.sleep(0.6) # Rate limiting prevention
        
        # Fetch Advanced stats
        advanced_stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            season_type_all_star=season_type,
            measure_type_detailed_defense='Advanced'
        ).get_data_frames()[0]
        
        time.sleep(0.6) # Rate limiting prevention

        # Columns that appear in both, we will drop the duplicates from advanced before merge
        overlap_cols = [col for col in base_stats.columns if col in advanced_stats.columns and col not in ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION']]
        advanced_stats = advanced_stats.drop(columns=overlap_cols)

        # Merge on Player and Team identifiers
        merged = pd.merge(base_stats, advanced_stats, on=['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION'])
        merged['SEASON'] = season # Add season column for tracking
        
        return merged
    
    except Exception as e:
        print(f"Error fetching data for {season}: {e}")
        return pd.DataFrame()

def main():
    print("Loading configuration...")
    config = load_config()
    start_season = config['data_collection']['start_season']
    end_season = config['data_collection']['end_season']
    season_type = config['data_collection']['season_type']
    min_games = config['data_collection']['min_games_played']
    
    features = []
    for category in config['features'].values():
        features.extend(category)
    
    seasons = generate_seasons(start_season, end_season)
    print(f"Fetching data for {len(seasons)} seasons: {start_season} to {end_season}")
    
    all_seasons_data = []
    for season in tqdm(seasons, desc="Fetching Seasons"):
        season_df = fetch_season_data(season, season_type)
        if not season_df.empty:
            all_seasons_data.append(season_df)
            
    if not all_seasons_data:
        print("No data was fetched.")
        return
        
    final_df = pd.concat(all_seasons_data, ignore_index=True)
    
    print(f"Raw data shape: {final_df.shape}")
    
    # Filter by minimum games played
    if 'GP' in final_df.columns:
        final_df = final_df[final_df['GP'] >= min_games]
        print(f"Shape after filtering for >= {min_games} games played: {final_df.shape}")
    
    # Ensure all requested features are present (some advanced stats might have slightly different names in the API)
    # The API generally uses these exact names, but it's good to verify.
    # Player identifiers and season to keep
    core_cols = ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'SEASON']
    available_features = [f for f in features if f in final_df.columns]
    
    missing = set(features) - set(available_features)
    if missing:
        print(f"Warning: The following features from config were not found in the API response: {missing}")
    
    final_cols = core_cols + available_features
    final_df = final_df[final_cols]
    
    # Sort data chronologically by Season and then alphabetically by Player Name
    final_df = final_df.sort_values(by=['SEASON', 'PLAYER_NAME']).reset_index(drop=True)
    
    # Save the data
    output_dir = "data/raw"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "nba_player_stats.csv")
    
    final_df.to_csv(output_path, index=False)
    print(f"Data successfully saved to {output_path}")

if __name__ == "__main__":
    main()
