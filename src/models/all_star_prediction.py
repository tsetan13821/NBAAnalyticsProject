import pandas as pd
import os
import warnings
warnings.filterwarnings('ignore')

CONFERENCES = {
    'EAST': ['BOS', 'BKN', 'NYK', 'NJN', 'PHI', 'TOR', 'CHI', 'CLE', 'DET', 'IND', 'MIL', 'ATL', 'CHA', 'MIA', 'ORL', 'WAS', 'CHH', 'CHO'],
    'WEST': ['DEN', 'MIN', 'OKC', 'POR', 'UTA', 'GSW', 'LAC', 'LAL', 'PHX', 'SAC', 'DAL', 'HOU', 'MEM', 'NOP', 'NOH', 'NOK', 'SEA', 'SAS', 'VAN', 'SAN']
}

def get_conference(team_abbr):
    if team_abbr in CONFERENCES['EAST']: return 'East'
    if team_abbr in CONFERENCES['WEST']: return 'West'
    return 'Unknown'

def assign_pos(row):
    gp = row['GP'] if row['GP'] > 0 else 1
    ast = row['AST'] / gp
    reb = row['REB'] / gp
    blk = row['BLK'] / gp
    
    # Manual overrides for superstar mold-breakers
    name = str(row['PLAYER_NAME']).strip()
    if name in ['LeBron James', 'Kevin Durant', 'Giannis Antetokounmpo', 'Kawhi Leonard', 'Jayson Tatum', 'Carmelo Anthony', 'Dirk Nowitzki', 'Tim Duncan']: return 'F'
    if name in ['Nikola Jokic', 'Nikola Jokic', 'Joel Embiid', 'Karl-Anthony Towns', 'Shaquille O\'Neal', 'Dwight Howard', 'Yao Ming']: return 'C'
    if name in ['Luka Doncic', 'Luka Doncic', 'James Harden', 'Stephen Curry', 'Russell Westbrook', 'Allen Iverson', 'Steve Nash', 'Kobe Bryant', 'Dwyane Wade']: return 'G'
    
    if reb >= 9.0 and blk >= 1.0: return 'C'
    if reb >= 10.0 and ast < 5.0: return 'C'
    if ast >= 5.5: return 'G'
    if ast >= 3.5 and reb < 5.0: return 'G'
    if reb >= 6.0: return 'F'
    if ast > reb: return 'G'
    return 'F'

def calculate_impact_score(row):
    gp = row['GP'] if row['GP'] > 0 else 1
    pts_pg = row['PTS'] / gp
    ast_pg = row['AST'] / gp
    reb_pg = row['REB'] / gp
    
    # Impact score logically heavily weighs PIE (Player Impact Estimate), Team Win%, and Raw Production
    return (row['PIE'] * 100) + (row['WinPCT'] * 30) + (pts_pg + ast_pg * 1.5 + reb_pg * 1.2) + (row['NET_RATING'] / 4)

def run_all_star_pipeline():
    raw_path = 'data/processed/mvp_data.csv'
    if not os.path.exists(raw_path):
        print("Required mvp_data.csv missing!")
        return
        
    df = pd.read_csv(raw_path)
    
    # 1. Map Conferences
    df['Conference'] = df['TEAM_ABBREVIATION'].apply(get_conference)
    
    # 2. Get team WinPCT per season
    # Let's get unique team performances per season
    teams = df[['SEASON', 'TEAM_ABBREVIATION', 'Conference', 'WinPCT']].drop_duplicates()
    
    # Rank teams in their conference
    teams['Conf_Seed'] = teams.groupby(['SEASON', 'Conference'])['WinPCT'].rank(ascending=False, method='min')
    
    # Merge seed back to main DF
    df = pd.merge(df, teams[['SEASON', 'TEAM_ABBREVIATION', 'Conf_Seed']], on=['SEASON', 'TEAM_ABBREVIATION'])
    
    # 3. Filter: Ignore below 10th seed
    eligible = df[df['Conf_Seed'] <= 10].copy()
    
    # Base filter for games played to filter out people who played 3 games
    eligible = eligible[eligible['GP'] >= 45]
    
    # 4. Map Positions
    eligible['POS'] = eligible.apply(assign_pos, axis=1)
    
    # 5. Calculate Impact Score
    eligible['IMPACT_SCORE'] = eligible.apply(calculate_impact_score, axis=1)
    
    # 6. Select Top 15 per Conference (6G, 6F, 3C)
    all_stars = []
    
    for season in eligible['SEASON'].unique():
        season_df = eligible[eligible['SEASON'] == season]
        
        for conf in ['East', 'West']:
            conf_df = season_df[season_df['Conference'] == conf].sort_values(by='IMPACT_SCORE', ascending=False)
            
            guards = conf_df[conf_df['POS'] == 'G'].head(6)
            forwards = conf_df[conf_df['POS'] == 'F'].head(6)
            centers = conf_df[conf_df['POS'] == 'C'].head(3)
            
            all_stars.append(guards)
            all_stars.append(forwards)
            all_stars.append(centers)
            
    final_all_stars = pd.concat(all_stars, ignore_index=True)
    
    # Flag them as ASTAR
    final_all_stars['IS_ALL_STAR'] = 1
    
    # Optional sorting
    final_all_stars = final_all_stars.sort_values(by=['SEASON', 'Conference', 'IMPACT_SCORE'], ascending=[False, True, False])
    
    # Save datasets
    os.makedirs('data/processed', exist_ok=True)
    
    master_path = 'data/processed/all_stars_master.csv'
    final_all_stars.to_csv(master_path, index=False)
    print(f"Saved {len(final_all_stars)} All-Stars to {master_path}")
    
    # Separate datasets by position! 
    for pos, name in [('G', 'guards'), ('F', 'forwards'), ('C', 'centers')]:
        pos_df = final_all_stars[final_all_stars['POS'] == pos]
        path = f'data/processed/all_stars_{name}.csv'
        pos_df.to_csv(path, index=False)
        print(f"Saved {len(pos_df)} {name} to {path}")

if __name__ == '__main__':
    run_all_star_pipeline()
