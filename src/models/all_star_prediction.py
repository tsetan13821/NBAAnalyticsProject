import pandas as pd

from src.nba_reference import get_conference, normalize_name
from src.paths import ALL_STARS_MASTER, MVP_DATA, PROCESSED_DIR

# Manual overrides for superstars whose box-score profile misleads the position heuristic.
# Names are compared accent-insensitively (see normalize_name).
POSITION_OVERRIDES = {
    'F': ['LeBron James', 'Kevin Durant', 'Giannis Antetokounmpo', 'Kawhi Leonard', 'Jayson Tatum',
          'Carmelo Anthony', 'Dirk Nowitzki', 'Tim Duncan'],
    'C': ['Nikola Jokic', 'Joel Embiid', 'Karl-Anthony Towns', "Shaquille O'Neal", 'Dwight Howard', 'Yao Ming'],
    'G': ['Luka Doncic', 'James Harden', 'Stephen Curry', 'Russell Westbrook', 'Allen Iverson', 'Steve Nash',
          'Kobe Bryant', 'Dwyane Wade'],
}
_OVERRIDE_LOOKUP = {normalize_name(name): pos for pos, names in POSITION_OVERRIDES.items() for name in names}


def assign_pos(row):
    override = _OVERRIDE_LOOKUP.get(normalize_name(row['PLAYER_NAME']))
    if override:
        return override

    gp = row['GP'] if row['GP'] > 0 else 1
    ast = row['AST'] / gp
    reb = row['REB'] / gp
    blk = row['BLK'] / gp

    if reb >= 9.0 and blk >= 1.0: return 'C'
    if reb >= 10.0 and ast < 5.0: return 'C'
    if ast >= 5.5: return 'G'
    if ast >= 3.5 and reb < 5.0: return 'G'
    if reb >= 6.0: return 'F'
    if ast > reb: return 'G'
    return 'F'


def calculate_impact_score(row):
    """Hand-weighted formula (not a trained model): PIE, team win%, per-game production and net rating."""
    gp = row['GP'] if row['GP'] > 0 else 1
    pts_pg = row['PTS'] / gp
    ast_pg = row['AST'] / gp
    reb_pg = row['REB'] / gp
    return (row['PIE'] * 100) + (row['WinPCT'] * 30) + (pts_pg + ast_pg * 1.5 + reb_pg * 1.2) + (row['NET_RATING'] / 4)


def run_all_star_pipeline():
    if not MVP_DATA.exists():
        print(f"Required {MVP_DATA} missing!")
        return

    df = pd.read_csv(MVP_DATA)

    # 1. Map Conferences
    df['Conference'] = [get_conference(team, season) for team, season in zip(df['TEAM_ABBREVIATION'], df['SEASON'])]

    # 2. Rank teams within their conference by WinPCT
    teams = df[['SEASON', 'TEAM_ABBREVIATION', 'Conference', 'WinPCT']].drop_duplicates()
    teams['Conf_Seed'] = teams.groupby(['SEASON', 'Conference'])['WinPCT'].rank(ascending=False, method='min')
    df = pd.merge(df, teams[['SEASON', 'TEAM_ABBREVIATION', 'Conf_Seed']], on=['SEASON', 'TEAM_ABBREVIATION'])

    # 3. Filter: ignore teams below the 10th seed and players with few games
    eligible = df[(df['Conf_Seed'] <= 10) & (df['GP'] >= 45)].copy()

    # 4. Map Positions and 5. Calculate Impact Score
    eligible['POS'] = eligible.apply(assign_pos, axis=1)
    eligible['IMPACT_SCORE'] = eligible.apply(calculate_impact_score, axis=1)

    # 6. Select Top 15 per Conference (6G, 6F, 3C)
    roster_slots = {'G': 6, 'F': 6, 'C': 3}
    all_stars = []
    for (_, conf), conf_df in eligible.groupby(['SEASON', 'Conference']):
        if conf not in ('East', 'West'):
            continue
        conf_df = conf_df.sort_values(by='IMPACT_SCORE', ascending=False)
        for pos, slots in roster_slots.items():
            all_stars.append(conf_df[conf_df['POS'] == pos].head(slots))

    final_all_stars = pd.concat(all_stars, ignore_index=True)
    final_all_stars['IS_ALL_STAR'] = 1
    final_all_stars = final_all_stars.sort_values(by=['SEASON', 'Conference', 'IMPACT_SCORE'], ascending=[False, True, False])

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    final_all_stars.to_csv(ALL_STARS_MASTER, index=False)
    print(f"Saved {len(final_all_stars)} All-Stars to {ALL_STARS_MASTER}")

    for pos, name in [('G', 'guards'), ('F', 'forwards'), ('C', 'centers')]:
        pos_df = final_all_stars[final_all_stars['POS'] == pos]
        path = PROCESSED_DIR / f'all_stars_{name}.csv'
        pos_df.to_csv(path, index=False)
        print(f"Saved {len(pos_df)} {name} to {path}")


if __name__ == '__main__':
    run_all_star_pipeline()
