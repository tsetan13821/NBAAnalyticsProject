import math
import random
from pathlib import Path

import pytest

from app.services.tree_model import TreeEnsemble

TRAINED_MODEL = Path(__file__).resolve().parents[2] / "saved_models" / "next_game_model.pkl"


def stump(feature: str, threshold: float, left: float, right: float) -> dict:
    """A one-split tree: `left` when feature < threshold, else `right`."""
    return {
        "nodeid": 0, "split": feature, "split_condition": threshold, "yes": 1, "no": 2,
        "children": [{"nodeid": 1, "leaf": left}, {"nodeid": 2, "leaf": right}],
    }


def model(*trees, base_score=0.5, objective="binary:logistic"):
    return TreeEnsemble({"objective": objective, "base_score": base_score, "features": ["x", "y"], "trees": trees})


def sigmoid(margin: float) -> float:
    return 1 / (1 + math.exp(-margin))


def test_no_trees_returns_base_score():
    assert model(base_score=0.3).predict_proba({"x": 0, "y": 0}) == pytest.approx(0.3)


def test_leaves_are_summed_on_the_logit_scale():
    ensemble = model(stump("x", 0.5, -1.0, 1.0), stump("y", 0.5, -0.5, 0.25))
    assert ensemble.predict_proba({"x": 0.9, "y": 0.1}) == pytest.approx(sigmoid(1.0 - 0.5))
    assert ensemble.predict_proba({"x": 0.1, "y": 0.9}) == pytest.approx(sigmoid(-1.0 + 0.25))


def test_value_equal_to_threshold_goes_right():
    # XGBoost sends a value to the "yes" branch only when it is strictly less than the split.
    ensemble = model(stump("x", 0.5, -2.0, 2.0))
    assert ensemble.predict_proba({"x": 0.5, "y": 0}) == pytest.approx(sigmoid(2.0))


def test_missing_feature_is_an_error():
    with pytest.raises(ValueError, match="Missing features"):
        model().predict_proba({"x": 0})


def test_only_binary_logistic_is_supported():
    with pytest.raises(ValueError, match="Unsupported objective"):
        model(objective="reg:squarederror")


def test_exported_model_matches_xgboost(settings):
    pytest.importorskip("xgboost")
    joblib = pytest.importorskip("joblib")
    pd = pytest.importorskip("pandas")
    if not TRAINED_MODEL.exists():
        pytest.skip(f"{TRAINED_MODEL} not found")

    exported = TreeEnsemble.from_file(settings.model_path)
    rng = random.Random(0)
    rows = []
    for _ in range(300):
        home, home_home, away, away_road = (rng.random() for _ in range(4))
        rows.append({
            "HOME_Overall_WinPCT": home, "HOME_Home_WinPCT": home_home,
            "AWAY_Overall_WinPCT": away, "AWAY_Away_WinPCT": away_road,
            "WinPCT_Diff": home - away, "HomeAway_Diff": home_home - away_road,
        })
    frame = pd.DataFrame(rows)[exported.features]

    expected = joblib.load(TRAINED_MODEL).predict_proba(frame)[:, 1]
    for row, want in zip(rows, expected, strict=True):
        assert exported.predict_proba(row) == pytest.approx(want, abs=1e-5)
