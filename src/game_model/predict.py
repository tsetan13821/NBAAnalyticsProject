"""Apply the saved game model: predicted home margin, and the home team's chance of winning."""
import json
import math

import numpy as np
import pandas as pd

from src.paths import GAME_MODEL


def load_model() -> dict:
    return json.loads(GAME_MODEL.read_text())


def win_probability(margin: float | np.ndarray, spread: float) -> np.ndarray:
    """P(final margin > 0) when the margin is normal around the prediction with this spread."""
    z = np.asarray(margin, dtype=float) / (spread * math.sqrt(2))
    return 0.5 * (1 + np.vectorize(math.erf)(z))


def predict(df: pd.DataFrame, model: dict) -> tuple[np.ndarray, np.ndarray]:
    margin = model['intercept'] + sum(df[f].to_numpy(dtype=float) * c for f, c in model['coefficients'].items())
    return margin, win_probability(margin, model['spread'])


def contributions(row: dict, model: dict) -> dict[str, float]:
    """Points each feature adds to the home team's predicted margin (the intercept is the home edge)."""
    return {'home_court': model['intercept'], **{f: row[f] * c for f, c in model['coefficients'].items()}}
