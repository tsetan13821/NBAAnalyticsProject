import pandas as pd
import time
import os
from nba_api.stats.endpoints import leaguestandings
from nba_api.stats.static import teams

def get_mvp_winners():
    """Returns a dictionary mapping Season -> MVP Player Name"""
    return {
        '2000-01': 'Allen Iverson',
        '2001-02': 'Tim Duncan',
        '2002-03': 'Tim Duncan',
        '2003-04': 'Kevin Garnett',
        '2004-05': 'Steve Nash',
        '2005-06': 'Steve Nash',
        '2006-07': 'Dirk Nowitzki',
        '2007-08': 'Kobe Bryant',
        '2008-09': 'LeBron James',
        '2009-10': 'LeBron James',
        '2010-11': 'Derrick Rose',
        '2011-12': 'LeBron James',
        '2012-13': 'LeBron James',
        '2013-14': 'Kevin Durant',
        '2014-15': 'Stephen Curry',
        '2015-16': 'Stephen Curry',
        '2016-17': 'Russell Westbrook',
        '2017-18': 'James Harden',
        '2018-19': 'Giannis Antetokounmpo',
        '2019-20': 'Giannis Antetokounmpo',
        '2020-21': 'Nikola Jokić',
        '2021-22': 'Nikola Jokić',
        '2022-23': 'Joel Embiid',
        '2023-24': 'Nikola Jokić',
        '2024-25': 'Shai Gilgeous-Alexander',
        '2025-26': 'Shai Gilgeous-Alexander' 
    }

def fetch_team_standings(seasons):
    """Fetches team standings for a list of seasons and returns a consolidated DataFrame."""
    all_standings = []
    
    # Get NBA teams to map TeamID to Abbreviation
    nba_teams = teams.get_teams()
    team_dict = {team['id']: team['abbreviation'] for team in nba_teams}
    
    print(f"Fetching team standings for {len(seasons)} seasons. This may take a moment to avoid rate limits...")
    
    for season in seasons:
        try:
            print(f"Fetching {season}...")
            standings = leaguestandings.LeagueStandings(season=season)
            df = standings.get_data_frames()[0]
            
            # Use 'TeamID' to map to standard abbreviations that match our player stats
            df['TEAM_ABBREVIATION'] = df['TeamID'].map(team_dict)
            df['SEASON'] = season
            
            # Extract relevant columns including point differential
            win_data = df[['TEAM_ABBREVIATION', 'SEASON', 'WINS', 'LOSSES', 'WinPCT', 'DiffPointsPG']]
            all_standings.append(win_data)
            
            # Sleep to strictly avoid being rate-limited by NBA API
            time.sleep(1.2)
        except Exception as e:
            print(f"Error fetching data for {season}: {e}")
            
    return pd.concat(all_standings, ignore_index=True)

def build_mvp_dataset():
    # Define paths
    raw_data_path = os.path.join('data', 'raw', 'nba_player_stats.csv')
    processed_dir = os.path.join('data', 'processed')
    output_path = os.path.join(processed_dir, 'mvp_data.csv')
    
    # Ensure processed directory exists
    os.makedirs(processed_dir, exist_ok=True)
    
    # 1. Load Player Stats
    print("Loading player stats...")
    df_players = pd.read_csv(raw_data_path)
    
    # Core MVP Features + Identifiers
    features_to_keep = [
        'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'SEASON', 'GP', 'MIN',
        'PTS', 'REB', 'AST', 'STL', 'BLK', 'DEF_RATING', 'AST_PCT', 'TS_PCT', 'USG_PCT', 'PIE', 'NET_RATING'
    ]
    # Filter to only the columns we need (if they exist in the raw dataset)
    available_cols = [col for col in features_to_keep if col in df_players.columns]
    df_players = df_players[available_cols].copy()
    
    # Get unique seasons in the dataset
    seasons = df_players['SEASON'].unique()
    
    # 2. Fetch Team Standings
    df_teams = fetch_team_standings(seasons)
    
    # 3. Merge Player Stats with Team Standings
    print("Merging player stats with team standings...")
    df_merged = pd.merge(df_players, df_teams, on=['TEAM_ABBREVIATION', 'SEASON'], how='left')
    
    # 4. Add the IS_MVP Target Column
    print("Adding IS_MVP target column...")
    mvp_dict = get_mvp_winners()
    
    def is_mvp(row):
        season = row['SEASON']
        if season in mvp_dict and row['PLAYER_NAME'] == mvp_dict[season]:
            return 1
        return 0
        
    df_merged['IS_MVP'] = df_merged.apply(is_mvp, axis=1)
    
    # 5. Clean / Handle NA values if needed
    # (e.g. drop rows lacking critical metrics)
    df_merged.dropna(subset=['PIE', 'TS_PCT', 'WINS'], inplace=True)
    
    # 6. Save the new dataset
    print(f"Saving MVP dataset with {len(df_merged)} rows to {output_path}...")
    df_merged.to_csv(output_path, index=False)
    print("Done!")

if __name__ == "__main__":
    build_mvp_dataset()