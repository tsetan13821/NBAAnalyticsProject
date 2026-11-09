"""Evaluate an exported XGBoost binary classifier without importing xgboost.

src/export_db.py writes the model with `Booster.get_dump(dump_format="json")`. Each tree is a nested
dict: internal nodes have `split`, `split_condition`, `yes`, `no` and `children`; leaves have `leaf`.
Prediction = sigmoid(logit(base_score) + sum of the leaf reached in every tree).
"""
import json
import math
from pathlib import Path


class TreeEnsemble:
    def __init__(self, model: dict):
        if model.get("objective") != "binary:logistic":
            raise ValueError(f"Unsupported objective: {model.get('objective')}")
        self.features: list[str] = list(model["features"])
        base_score = float(model["base_score"])
        self._base_margin = math.log(base_score / (1 - base_score))
        # Flatten each tree into {node_id: node} so walking it is a dict lookup per level.
        self._trees = [self._index(tree) for tree in model["trees"]]

    @classmethod
    def from_file(cls, path: Path) -> "TreeEnsemble":
        return cls(json.loads(Path(path).read_text()))

    @staticmethod
    def _index(root: dict) -> dict[int, dict]:
        nodes, stack = {}, [root]
        while stack:
            node = stack.pop()
            nodes[node["nodeid"]] = node
            stack.extend(node.get("children", ()))
        return nodes

    def predict_proba(self, features: dict[str, float]) -> float:
        missing = set(self.features) - features.keys()
        if missing:
            raise ValueError(f"Missing features: {sorted(missing)}")

        margin = self._base_margin
        for nodes in self._trees:
            node = nodes[0]
            while "leaf" not in node:
                value = features[node["split"]]
                node = nodes[node["yes"] if value < node["split_condition"] else node["no"]]
            margin += node["leaf"]
        return 1.0 / (1.0 + math.exp(-margin))
