import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report
import warnings
warnings.filterwarnings('ignore')

def apply_mvp_candidate_filters(df):
    """
    Applies domain-knowledge filters to drastically reduce the noise in MVP predictions.
    1. WinPCT must be >= 55% (0.55).
    2. If WinPCT is between 55% and 65%, the player must have extraordinary individual 
       stats (e.g., PIE >= 0.18 and USG_PCT >= 0.28) to remain a candidate.
    3. Must play a minimum number of games (e.g., >= 58, scaled for lockouts/short seasons).
    """
    print(f"Original dataset size: {len(df)}")
    
    # Keep only players with >= 55% WinPCT
    df = df[df['WinPCT'] >= 0.55].copy()
    
    # Strict rule for 55% - 65% WinPCT (The Westbrook Rule)
    # If the team was just "good", the player needs to be historically great individually
    extraordinary_condition = (df['PIE'] >= 0.18) & (df['USG_PCT'] >= 0.28)
    elite_team_condition = (df['WinPCT'] >= 0.65)
    
    # Keep if they are on an elite team OR they had an extraordinary season on a good team
    df = df[elite_team_condition | extraordinary_condition]
    
    # Base availability
    df = df[df['GP'] >= 50]
    
    # Remove pure role players who happen to be on elite teams
    # MVPs must carry a heavy offensive load and have high overall impact. 
    # Historically, almost NO MVP has had a Usage Rate < 20% or PIE < 14%. 
    # We'll use USG_PCT >= 18% and PIE >= 12% as a safe absolute floor.
    df = df[(df['USG_PCT'] >= 0.18) & (df['PIE'] >= 0.12)]
    
    # Needs to score or generate points (e.g. 1000 points or huge assists)
    df = df[(df['PTS'] + (df['AST'] * 2)) >= 1200]
    
    print(f"Filtered candidate size: {len(df)}")
    return df

def feature_engineering(df):
    """
    Calculates Z-scores for players relative to their SEASON.
    This neutralizes the effects of pace and era inflation.
    """
    # 1. Total Offensive Load
    df['OFFENSIVE_LOAD'] = df['USG_PCT'] + df['AST_PCT']
    
    # 2. Defensive Impact (Stocks)
    df['STOCKS'] = df['STL'] + df['BLK']
    
    # 3. Seed Ranking Proxy
    df['SEED_RANK'] = df.groupby('SEASON')['WinPCT'].rank(ascending=False, method='min')
    
    # NEW RULE: Historically, MVPs almost exclusively come from a Top 2 Seed in their conference
    # We create a hard flag for whether they are on an elite #1 or #2 overall WinPCT pace
    df['IS_TOP_2_SEED'] = (df['SEED_RANK'] <= 2).astype(int)
    
    # 4. Voter Fatigue (Did they win last year?)
    mw_dict = {
        '1999-00': 'Shaquille O\'Neal', '2000-01': 'Allen Iverson', '2001-02': 'Tim Duncan',
        '2002-03': 'Tim Duncan', '2003-04': 'Kevin Garnett', '2004-05': 'Steve Nash',
        '2005-06': 'Steve Nash', '2006-07': 'Dirk Nowitzki', '2007-08': 'Kobe Bryant',
        '2008-09': 'LeBron James', '2009-10': 'LeBron James', '2010-11': 'Derrick Rose',
        '2011-12': 'LeBron James', '2012-13': 'LeBron James', '2013-14': 'Kevin Durant',
        '2014-15': 'Stephen Curry', '2015-16': 'Stephen Curry', '2016-17': 'Russell Westbrook',
        '2017-18': 'James Harden', '2018-19': 'Giannis Antetokounmpo', '2019-20': 'Giannis Antetokounmpo',
        '2020-21': 'Nikola Jokić', '2021-22': 'Nikola Jokić', '2022-23': 'Joel Embiid',
        '2023-24': 'Nikola Jokić', '2024-25': 'Shai Gilgeous-Alexander'
    }
    
    def check_fatigue(row):
        try:
            y1, y2 = row['SEASON'].split('-')
            prev_season = f"{int(y1)-1}-{int(y2)-1:02d}"
            if mw_dict.get(prev_season) == row['PLAYER_NAME']:
                return 1
        except:
            pass
        return 0
        
    df['WON_LAST_YEAR'] = df.apply(check_fatigue, axis=1)

    # 5. On/Off Proxy:
    df['ON_OFF_PROXY'] = df['NET_RATING'] - df['DiffPointsPG']
    
    features = ['PTS', 'REB', 'AST', 'TS_PCT', 'OFFENSIVE_LOAD', 'PIE', 'ON_OFF_PROXY', 'WinPCT', 'STOCKS', 'DEF_RATING', 'GP']
    z_features = []
    
    for col in features:
        z_colName = f'{col}_Z'
        if col == 'DEF_RATING':
            # Invert DEF_RATING so lower is better (positive Z score)
            df[z_colName] = df.groupby('SEASON')[col].transform(lambda x: ((x - x.mean()) / x.std()) * -1)
        else:
            df[z_colName] = df.groupby('SEASON')[col].transform(lambda x: (x - x.mean()) / x.std())
        z_features.append(z_colName)
        
    # Appending the non-Z scored engineered features
    z_features.extend(['SEED_RANK', 'WON_LAST_YEAR'])
        
    return df, z_features

def test_season(df, z_features, target_season):
    """
    Trains on seasons EXCEPT the target_season within its specific ERA.
    Era 1: 2000-2007 (The Hero Ball Era)
    Era 2: 2008-2026 (The Analytics Era)
    """
    df['START_YEAR'] = df['SEASON'].astype(str).str.split('-').str[0].astype(int)
    target_year = int(target_season.split('-')[0])
    
    # Determine strict era boundaries so models only learn from relevant timeframes
    if target_year <= 2007:
        era_df = df[df['START_YEAR'] <= 2007].copy()
        
        # In Era 1, voters historically didn't care about PIE or OFFENSIVE_LOAD. 
        # They cared wildly about raw SEED_RANK and raw TRADITIONAL STATS.
        # We manually select and prioritize features meant for the early 2000s.
        era_features = ['PTS_Z', 'REB_Z', 'AST_Z', 'WinPCT_Z', 'STOCKS_Z', 'SEED_RANK', 'IS_TOP_2_SEED', 'WON_LAST_YEAR']
    else:
        era_df = df[df['START_YEAR'] > 2007].copy()
        
        # In Era 2, voters heavily care about ADVANCED STATS and carry weight.
        # They ignore traditional stats and heavily scrutinize PIE, On/Off, and TS%.
        era_features = ['TS_PCT_Z', 'OFFENSIVE_LOAD_Z', 'PIE_Z', 'ON_OFF_PROXY_Z', 'SEED_RANK', 'IS_TOP_2_SEED', 'DEF_RATING_Z', 'GP_Z']
        
    # 1. Split Data using ONLY the Era-Specific Features
    train_data = era_df[era_df['SEASON'] != target_season].copy()
    test_data = era_df[era_df['SEASON'] == target_season].copy()
    
    if len(test_data) == 0:
        return None

    X_train = train_data[era_features]
    y_train = train_data['IS_MVP']
    
    X_test = test_data[era_features]
    y_test = test_data['IS_MVP']
    
    # 2. Train Model
    # scale_pos_weight is high because non-MVPs heavily outnumber MVPs
    model = XGBClassifier(
        n_estimators=100, 
        learning_rate=0.1, 
        max_depth=3, 
        scale_pos_weight=50, 
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # 3. Predict Probabilities
    test_data['MVP_PROB_SCORE'] = model.predict_proba(X_test)[:, 1]
    
    # 4. Rank Candidates
    predictions = test_data.sort_values(by='MVP_PROB_SCORE', ascending=False)
    predicted_mvp = predictions.iloc[0]
    actual_mvp = test_data[test_data['IS_MVP'] == 1]
    
    actual_mvp_name = actual_mvp['PLAYER_NAME'].values[0] if not actual_mvp.empty else "None"
    
    return {
        'SEASON': target_season,
        'PREDICTED_MVP': predicted_mvp['PLAYER_NAME'],
        'ACTUAL_MVP': actual_mvp_name,
        'CORRECT': predicted_mvp['PLAYER_NAME'] == actual_mvp_name,
        'TOP_10_CANDIDATES': predictions[['PLAYER_NAME', 'MVP_PROB_SCORE']].head(10).to_dict('records'),
        'Y_TRUE': test_data['IS_MVP'].values,
        'Y_PRED': (test_data['PLAYER_NAME'] == predicted_mvp['PLAYER_NAME']).astype(int).values
    }

def run_loocv():
    """Runs Leave-One-Season-Out Cross Validation"""
    # Load data
    df = pd.read_csv('data/processed/mvp_data.csv')
    
    # Apply our domain-knowledge heuristic rules
    df = apply_mvp_candidate_filters(df)
    
    # Feature Engineering
    df, z_features = feature_engineering(df)
    
    # Fill NAs mathematically caused by Z-scoring single items or zero variance
    df[z_features] = df[z_features].fillna(0)
    
    seasons = sorted(df['SEASON'].unique())
    results = []
    correct_count = 0
    all_y_true = []
    all_y_pred = []
    
    for season in seasons:
        res = test_season(df, z_features, season)
        if res:
            results.append(res)
            all_y_true.extend(res['Y_TRUE'])
            all_y_pred.extend(res['Y_PRED'])
            if res['CORRECT']: correct_count += 1
            
    return {
        'results': results,
        'accuracy_str': f"{correct_count}/{len(results)} ({(correct_count/len(results))*100:.1f}%)",
        'y_true': all_y_true,
        'y_pred': all_y_pred
    }

def run_loocv_cli():
    """Runs Leave-One-Season-Out Cross Validation and prints to CLI"""
    res_dict = run_loocv()
    if not res_dict: return
    
    print("\n--- Running Leave-One-Season-Out Prediction ---")
    for res in res_dict['results']:
        match_status = "✅" if res['CORRECT'] else "❌"
        print(f"{res['SEASON']}: Predicted = {res['PREDICTED_MVP']} | Actual = {res['ACTUAL_MVP']} {match_status}")
            
    print("-" * 50)
    print(f"Overall Accuracy: {res_dict['accuracy_str']}")
    
    print("\n--- Classification Report ---")
    print(classification_report(res_dict['y_true'], res_dict['y_pred'], target_names=['Not MVP (0)', 'MVP (1)']))

def analyze_specific_season(target_season='2023-24'):
    """Analyze a single target season and print detailed probabilities."""
    df = pd.read_csv('data/processed/mvp_data.csv')
    df = apply_mvp_candidate_filters(df)
    df, z_features = feature_engineering(df)
    df[z_features] = df[z_features].fillna(0)
    
    print(f"\n--- Analyzing MVP Race for {target_season} ---")
    res = test_season(df, z_features, target_season)
    
    if res:
        print(f"👑 Predicted MVP: {res['PREDICTED_MVP']}")
        print(f"🏆 Actual MVP:    {res['ACTUAL_MVP']}")
        print("\n📊 Top 10 Candidates based on Model Probability:")
        for rank, candidate in enumerate(res['TOP_10_CANDIDATES'], 1):
            print(f"{rank}. {candidate['PLAYER_NAME']} (Score: {candidate['MVP_PROB_SCORE']:.4f})")
    else:
        print(f"No data found for {target_season}")

if __name__ == "__main__":
    run_loocv_cli()
    # analyze_specific_season('2005-06')