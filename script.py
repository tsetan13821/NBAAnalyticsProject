import pandas as pd
from src.models.mvp_prediction import apply_mvp_candidate_filters, feature_engineering, test_season

df = pd.read_csv('data/processed/mvp_data.csv')
df = apply_mvp_candidate_filters(df)
df, z_features = feature_engineering(df)
df['IS_TOP_2_SEED'] = (df['SEED_RANK'] <= 2).astype(int)
df['IS_TOP_3_SEED'] = (df['SEED_RANK'] <= 3).astype(int)
df[z_features] = df[z_features].fillna(0)
df['START_YEAR'] = df['SEASON'].astype(str).str.split('-').str[0].astype(int)

def evaluate_era1(features):
    era1_seasons = [s for s in df[df['START_YEAR'] <= 2007]['SEASON'].unique()]
    df_era1 = df[df['START_YEAR'] <= 2007].copy()
    correct = 0
    from xgboost import XGBClassifier
    for season in era1_seasons:
        train = df_era1[df_era1['SEASON'] != season]
        test = df_era1[df_era1['SEASON'] == season]
        if len(test) == 0: continue
        model = XGBClassifier(n_estimators=100, learning_rate=0.05, max_depth=2, scale_pos_weight=50, random_state=42)
        model.fit(train[features], train['IS_MVP'])
        test['PROB'] = model.predict_proba(test[features])[:, 1]
        pred_mvp = test.loc[test['PROB'].idxmax(), 'PLAYER_NAME']
        actual_mvps = test.loc[test['IS_MVP'] == 1, 'PLAYER_NAME'].values
        actual_mvp = actual_mvps[0] if len(actual_mvps)>0 else "NONE"
        if pred_mvp == actual_mvp:
            correct += 1
            print(f"{season}: ? {pred_mvp}")
        else:
            print(f"{season}: ? Pred: {pred_mvp} | Act: {actual_mvp}")
    print(f"Correct: {correct}/8\n")

print("Trial (Top Seed + PTS + AST):")
evaluate_era1(['PTS_Z', 'AST_Z', 'IS_TOP_2_SEED', 'WON_LAST_YEAR'])
evaluate_era1(['PTS_Z', 'REB_Z', 'AST_Z', 'IS_TOP_2_SEED', 'WON_LAST_YEAR', 'ON_OFF_PROXY_Z'])
evaluate_era1(['PTS_Z', 'REB_Z', 'AST_Z', 'IS_TOP_3_SEED', 'WON_LAST_YEAR', 'ON_OFF_PROXY_Z', 'WinPCT_Z'])

