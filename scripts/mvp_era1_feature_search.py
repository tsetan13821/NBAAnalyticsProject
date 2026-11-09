"""Exploratory: compare candidate feature sets for the 2000-01..2007-08 ("Hero Ball") MVP era.

This is how the Era 1 features in src/models/mvp_prediction.py were explored. Note that choosing
features this way, by looking at leave-one-season-out results, makes the reported accuracy optimistic.

Run from the repository root:
    python -m scripts.mvp_era1_feature_search
"""
import pandas as pd
from xgboost import XGBClassifier

from src.models.mvp_prediction import apply_mvp_candidate_filters, feature_engineering
from src.paths import MVP_DATA

ERA1_LAST_START_YEAR = 2007


def load_era1():
    df = apply_mvp_candidate_filters(pd.read_csv(MVP_DATA))
    df, z_features = feature_engineering(df)
    df['IS_TOP_3_SEED'] = (df['SEED_RANK'] <= 3).astype(int)
    df[z_features] = df[z_features].fillna(0)
    df['START_YEAR'] = df['SEASON'].astype(str).str.split('-').str[0].astype(int)
    return df[df['START_YEAR'] <= ERA1_LAST_START_YEAR].copy()


def evaluate_era1(df_era1, features):
    seasons = sorted(df_era1['SEASON'].unique())
    correct = 0
    for season in seasons:
        train = df_era1[df_era1['SEASON'] != season]
        test = df_era1[df_era1['SEASON'] == season].copy()
        model = XGBClassifier(n_estimators=100, learning_rate=0.05, max_depth=2, scale_pos_weight=50, random_state=42)
        model.fit(train[features], train['IS_MVP'])
        test['PROB'] = model.predict_proba(test[features])[:, 1]
        predicted = test.loc[test['PROB'].idxmax(), 'PLAYER_NAME']
        actual = test.loc[test['IS_MVP'] == 1, 'PLAYER_NAME']
        actual = actual.iloc[0] if len(actual) else "NONE"
        hit = predicted == actual
        correct += hit
        print(f"{season}: {'HIT ' if hit else 'MISS'} predicted {predicted} | actual {actual}")
    print(f"Correct: {correct}/{len(seasons)}\n")


if __name__ == "__main__":
    era1 = load_era1()
    for features in [
        ['PTS_Z', 'AST_Z', 'IS_TOP_2_SEED', 'WON_LAST_YEAR'],
        ['PTS_Z', 'REB_Z', 'AST_Z', 'IS_TOP_2_SEED', 'WON_LAST_YEAR', 'ON_OFF_PROXY_Z'],
        ['PTS_Z', 'REB_Z', 'AST_Z', 'IS_TOP_3_SEED', 'WON_LAST_YEAR', 'ON_OFF_PROXY_Z', 'WinPCT_Z'],
    ]:
        print(f"Features: {features}")
        evaluate_era1(era1, features)
