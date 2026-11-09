import json
import math
import sqlite3

from app.errors import BadRequestError, NotFoundError
from app.repositories import games as games_repo
from app.services.game_model import GameModel, capped_value, win_probability

CONFIDENCE_EDGES = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)


def _team_value(players: list[dict], chance_of: dict[int, float]) -> float:
    return capped_value([(p["rate_above"], p["minutes"], chance_of[p["id"]]) for p in players])


def game_detail(
    conn: sqlite3.Connection, model: GameModel, game_id: str, out: list[int], in_: list[int]
) -> dict:
    found = games_repo.get_game(conn, game_id)
    if found is None:
        raise NotFoundError(f"Game {game_id} not found")
    summary, features = found
    players = games_repo.get_players(conn, game_id)

    out_set, in_set = set(out), set(in_)
    if out_set & in_set:
        raise BadRequestError(f"Players {sorted(out_set & in_set)} are both out and in")
    unknown = (out_set | in_set) - {p["id"] for p in players}
    if unknown:
        raise BadRequestError(f"Players {sorted(unknown)} are not on either roster for game {game_id}")

    base_margin = model.margin(features)
    if out_set or in_set:
        before = {p["id"]: p["chance"] for p in players}
        after = {pid: 0.0 if pid in out_set else 1.0 if pid in in_set else c for pid, c in before.items()}
        change = {}
        for side in ("home", "away"):
            team = [p for p in players if p["team_abbr"] == summary[side]["team"]["abbr"]]
            change[side] = _team_value(team, after) - _team_value(team, before)
        features = {**features, "AVAIL_DIFF": features["AVAIL_DIFF"] + change["home"] - change["away"]}
        for p in players:
            if p["id"] in out_set or p["id"] in in_set:
                p["chance"], p["what_if"] = after[p["id"]], "out" if p["id"] in out_set else "in"

    margin = model.margin(features)
    prob = win_probability(margin, model.spread)
    for p in players:
        del p["rate_above"], p["minutes"]
    detail = {
        **summary,
        "home_win_probability": round(prob, 4),
        "predicted_margin": round(margin, 1),
        "favorite": summary["home"]["team"]["abbr"] if prob >= 0.5 else summary["away"]["team"]["abbr"],
        "breakdown": model.breakdown(features),
        "spread": model.spread,
        "home_players": [p for p in players if p["team_abbr"] == summary["home"]["team"]["abbr"]],
        "away_players": [p for p in players if p["team_abbr"] == summary["away"]["team"]["abbr"]],
        "what_if": None,
    }
    if out_set or in_set:
        detail["what_if"] = {
            "out": sorted(out_set), "in": sorted(in_set),
            "base_home_win_probability": round(win_probability(base_margin, model.spread), 4),
            "base_predicted_margin": round(base_margin, 1),
        }
    if summary["result"]:
        home_won = summary["result"]["winner"] == summary["home"]["team"]["abbr"]
        detail["result"] = {**summary["result"], "correct": (prob >= 0.5) == home_won}
    return detail


def track_record(conn: sqlite3.Connection, team: str | None) -> dict:
    outcomes = games_repo.played_outcomes(conn, team)
    n = len(outcomes)
    record = {
        "season": games_repo.current_season(conn), "games": n, "correct": 0, "accuracy": None, "log_loss": None,
        "brier": None, "home_team_won": None, "by_confidence": [],
    }
    if not n:
        return record
    correct = sum((p >= 0.5) == bool(won) for p, won in outcomes)
    clipped = [(min(max(p, 1e-6), 1 - 1e-6), won) for p, won in outcomes]
    record.update(
        correct=correct,
        accuracy=round(correct / n, 4),
        log_loss=round(-sum(math.log(p if won else 1 - p) for p, won in clipped) / n, 4),
        brier=round(sum((p - won) ** 2 for p, won in outcomes) / n, 4),
        home_team_won=round(sum(won for _, won in outcomes) / n, 4),
    )
    for low, high in zip(CONFIDENCE_EDGES, CONFIDENCE_EDGES[1:], strict=False):
        favorites = [
            (max(p, 1 - p), (p >= 0.5) == bool(won))
            for p, won in outcomes
            if low <= max(p, 1 - p) < high or (high == 1.0 and max(p, 1 - p) == 1.0)
        ]
        if favorites:
            record["by_confidence"].append({
                "low": low, "high": high, "games": len(favorites),
                "favorite_won": sum(won for _, won in favorites),
                "predicted": round(sum(p for p, _ in favorites) / len(favorites), 4),
            })
    return record


def model_details(model: GameModel, metrics_json: str) -> dict:
    metrics = json.loads(metrics_json)
    return {
        "trained_on": model.trained_on,
        "intercept": model.intercept,
        "spread": model.spread,
        "play_rates": model.play_rates,
        "features": model.describe(),
        "evaluation": {
            **{k: metrics[k] for k in (
                "train_first_season", "train_last_season", "train_games", "test_season", "test_games",
                "held_out", "baselines", "models", "walk_forward",
            )},
            "ablation": [r for r in metrics["ablation"]],
            "calibration": [
                {"low": b["from"], "high": b["to"], "games": b["games"], "predicted": b["predicted"],
                 "actual": b["actual"]}
                for b in metrics["calibration"]
            ],
        },
    }
