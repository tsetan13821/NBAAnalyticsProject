"""Train and evaluate the game model.

    python -m src.game_model.train        # needs data/processed/game_features.csv.gz (src.game_model.features)

The model predicts the home team's winning margin with a ridge regression on the features (each in
points or per 100 possessions), and turns the margin into a win probability with a normal
distribution. Its spread is fitted to the training games' wins and losses (about 12.5 points;
the raw error of the margin, about 13.7, makes the probabilities too timid). A linear model keeps every
prediction explainable ("home court +2.4, Luka out -4.8") and, on ~7,000 games, holds its own
against gradient boosting; both alternatives are scored here for comparison.

Evaluation (all on games the model never saw):
    held out    train on the injury-report seasons before the last completed season, test on it
    walk forward  the same for each of the last four completed seasons in turn
    baselines   home team, better record, Elo alone
    ablation    feature groups added one at a time, to show what each adds
    calibration games grouped by predicted probability, against how often the favourite won
    actual availability  the same model given who really played (unknowable beforehand), to show
                what the uncertainty of the injury report costs

Writes saved_models/game_model.json (coefficients, spread, injury play rates) and
saved_models/game_model_metrics.json.
"""
import json
from itertools import pairwise

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
from xgboost import XGBClassifier

from src.game_model.features import FEATURE_GROUPS, FEATURES, build_features
from src.game_model.games import ELO_PER_POINT, elo_home_edge
from src.game_model.predict import win_probability
from src.game_model.seasons import configured_seasons
from src.paths import GAME_FEATURES, GAME_MODEL, GAME_MODEL_METRICS, MODELS_DIR

RIDGE_ALPHA = 1.0
WALK_FORWARD_SEASONS = 4


class MarginModel:
    """Ridge regression for the margin; win probability = P(normal(margin, spread) > 0)."""

    def __init__(self, features: list[str]):
        self.features = features
        self.ridge = Ridge(alpha=RIDGE_ALPHA)
        self.spread = 12.0

    def fit(self, df: pd.DataFrame) -> "MarginModel":
        self.ridge.fit(df[self.features], df['MARGIN'])
        margin, won = self.ridge.predict(df[self.features]), df['HOME_WIN'].to_numpy()

        def loss(spread: float) -> float:
            p = np.clip(win_probability(margin, spread), 1e-9, 1 - 1e-9)
            return float(-np.mean(won * np.log(p) + (1 - won) * np.log(1 - p)))

        self.spread = float(minimize_scalar(loss, bounds=(6.0, 20.0), method='bounded').x)
        return self

    def margin(self, df: pd.DataFrame) -> np.ndarray:
        return self.ridge.predict(df[self.features])

    def probability(self, df: pd.DataFrame) -> np.ndarray:
        return win_probability(self.margin(df), self.spread)


def scores(y: np.ndarray, p: np.ndarray) -> dict:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {
        'accuracy': round(float(accuracy_score(y, p >= 0.5)), 4),
        'log_loss': round(float(log_loss(y, p, labels=[0, 1])), 4),
        'brier': round(float(brier_score_loss(y, p)), 4),
    }


def elo_probability(df: pd.DataFrame) -> np.ndarray:
    """Elo alone, with its own home edge (the same one the ratings were built with)."""
    edge = np.array([elo_home_edge(row) for row in df[['BUBBLE', 'NEUTRAL_SITE', 'REDUCED_CROWD']].to_dict('records')])
    diff = df['ELO_DIFF'] * ELO_PER_POINT + edge
    return 1 / (1 + 10 ** (-diff / 400))


def baselines(test: pd.DataFrame) -> dict:
    y = test['HOME_WIN'].to_numpy()
    record = np.where(test['HOME_WIN_PCT'] >= test['AWAY_WIN_PCT'], 1.0, 0.0)
    return {
        'home_team': round(float(y.mean()), 4),
        'better_record': round(float(accuracy_score(y, record)), 4),
        'elo': scores(y, elo_probability(test)),
    }


def compare_models(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    y = test['HOME_WIN'].to_numpy()
    margin_model = MarginModel(FEATURES).fit(train)
    logistic = LogisticRegression(max_iter=2000, C=1.0).fit(train[FEATURES], train['HOME_WIN'])
    boosted = XGBClassifier(n_estimators=300, learning_rate=0.03, max_depth=3, subsample=0.8,
                            random_state=42, eval_metric='logloss').fit(train[FEATURES], train['HOME_WIN'])
    return {
        'margin_ridge': {**scores(y, margin_model.probability(test)),
                         'margin_mae': round(float(np.mean(np.abs(margin_model.margin(test) - test['MARGIN']))), 2)},
        'logistic': scores(y, logistic.predict_proba(test[FEATURES])[:, 1]),
        'xgboost': scores(y, boosted.predict_proba(test[FEATURES])[:, 1]),
    }


def ablation(train: pd.DataFrame, test: pd.DataFrame) -> list[dict]:
    y = test['HOME_WIN'].to_numpy()
    rows, features = [], []
    for group, columns in FEATURE_GROUPS.items():
        features = features + columns
        model = MarginModel(features).fit(train)
        rows.append({'added': group, 'features': list(features), **scores(y, model.probability(test))})
    # The same model, but told who really played (not knowable before the game)
    actual = train.assign(AVAIL_DIFF=train['AVAIL_ACTUAL_DIFF'])
    model = MarginModel(FEATURES).fit(actual)
    rows.append({'added': 'availability (who actually played)', 'features': FEATURES,
                 **scores(y, model.probability(test.assign(AVAIL_DIFF=test['AVAIL_ACTUAL_DIFF'])))})
    return rows


def calibration(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict]:
    """Bins of the favourite's predicted chance, with how often the favourite actually won."""
    favourite = np.maximum(p, 1 - p)
    won = np.where(p >= 0.5, y, 1 - y)
    edges = np.linspace(0.5, 1.0, bins + 1)
    rows = []
    for lo, hi in pairwise(edges):
        mask = (favourite >= lo) & (favourite < hi if hi < 1 else favourite <= hi)
        if mask.sum():
            rows.append({'from': round(lo, 2), 'to': round(hi, 2), 'games': int(mask.sum()),
                         'predicted': round(float(favourite[mask].mean()), 4),
                         'actual': round(float(won[mask].mean()), 4)})
    return rows


def split(df: pd.DataFrame, test_season: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    usable = df[df['HAS_INJURY_REPORT']]
    return usable[usable['SEASON'] < test_season], usable[usable['SEASON'] == test_season]


def train_game_model(rebuild_features: bool = True) -> dict:
    seasons = configured_seasons()
    if rebuild_features or not GAME_FEATURES.exists():
        df, play_rates = build_features()
        df.to_csv(GAME_FEATURES, index=False, compression='gzip')
    else:
        df = pd.read_csv(GAME_FEATURES, dtype={'GAME_ID': str})
        play_rates = json.loads(GAME_MODEL.read_text())['play_rates']

    completed = sorted(s for s in df.loc[df['HAS_INJURY_REPORT'], 'SEASON'].unique() if s <= seasons.completed)
    test_season = completed[-1]
    train, test = split(df, test_season)
    y = test['HOME_WIN'].to_numpy()
    print(f"Training on {len(train):,} games ({train['SEASON'].min()} to {train['SEASON'].max()}), "
          f"testing on {len(test):,} games of {test_season}")

    model = MarginModel(FEATURES).fit(train)
    p = model.probability(test)
    held_out = {**scores(y, p), 'margin_mae': round(float(np.mean(np.abs(model.margin(test) - test['MARGIN']))), 2)}
    # The old model skipped games before both teams had played ten; score that subset too, to compare like for like
    later = (test['HOME_GP'] >= 10) & (test['AWAY_GP'] >= 10)
    held_out_after_10 = scores(y[later.to_numpy()], p[later.to_numpy()])

    walk_forward = []
    for season in completed[-WALK_FORWARD_SEASONS:]:
        tr, te = split(df, season)
        m = MarginModel(FEATURES).fit(tr)
        walk_forward.append({'season': season, 'train_games': len(tr), 'test_games': len(te),
                             **scores(te['HOME_WIN'].to_numpy(), m.probability(te)),
                             'baselines': baselines(te)})

    metrics = {
        'train_first_season': train['SEASON'].min(),
        'train_last_season': train['SEASON'].max(),
        'train_games': len(train),
        'test_season': test_season,
        'test_games': len(test),
        'held_out': held_out,
        'held_out_after_10_games': {**held_out_after_10, 'games': int(later.sum())},
        'baselines': baselines(test),
        'models': compare_models(train, test),
        'ablation': ablation(train, test),
        'calibration': calibration(y, p),
        'walk_forward': walk_forward,
        'play_rates': play_rates,
    }

    # The deployed model learns from every completed season with injury reports, the held-out one included
    final = MarginModel(FEATURES).fit(df[df['HAS_INJURY_REPORT'] & (df['SEASON'] <= seasons.completed)])
    artifact = {
        'features': FEATURES,
        'groups': FEATURE_GROUPS,
        'coefficients': {f: round(float(c), 6) for f, c in zip(FEATURES, final.ridge.coef_)},
        'intercept': round(float(final.ridge.intercept_), 6),
        'spread': round(final.spread, 4),
        'play_rates': play_rates,
        'trained_on': f"{completed[0]} to {completed[-1]}",
    }
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    GAME_MODEL.write_text(json.dumps(artifact, indent=2) + "\n")
    GAME_MODEL_METRICS.write_text(json.dumps(metrics, indent=2) + "\n")
    _report(metrics, artifact)
    return metrics


def _report(metrics: dict, artifact: dict) -> None:
    b = metrics['baselines']
    print(f"\nHeld-out {metrics['test_season']}: {metrics['held_out']}")
    print(f"  after both teams' 10th game: {metrics['held_out_after_10_games']}")
    print(f"  baselines: home {b['home_team']}, better record {b['better_record']}, Elo {b['elo']}")
    print("Models:", json.dumps(metrics['models']))
    print("Ablation:")
    for row in metrics['ablation']:
        print(f"  + {row['added']:<36} acc {row['accuracy']:.4f}  log loss {row['log_loss']:.4f}  brier {row['brier']:.4f}")
    print("Walk forward:")
    for row in metrics['walk_forward']:
        print(f"  {row['season']}: acc {row['accuracy']:.4f}  log loss {row['log_loss']:.4f}  "
              f"(Elo {row['baselines']['elo']['accuracy']:.4f}, record {row['baselines']['better_record']:.4f})")
    print("Calibration:", [(r['predicted'], r['actual'], r['games']) for r in metrics['calibration']])
    print("Coefficients:", artifact['coefficients'], "intercept", artifact['intercept'], "spread", artifact['spread'])


if __name__ == "__main__":
    train_game_model()
