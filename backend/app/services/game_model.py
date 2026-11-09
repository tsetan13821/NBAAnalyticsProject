"""The game model at serving time: re-weighting who plays (what-ifs) and explaining a prediction.

The pipeline (src/game_model) computes every input; the API only changes players' chance of playing
and re-adds the coefficients. `capped_value` and `win_probability` mirror src/game_model/availability
and src/game_model/predict, which the tests check against stored predictions.
"""
import json
import math
from dataclasses import dataclass

TEAM_MINUTES = 240.0

GROUP_LABELS = {
    "home": "Home court",
    "strength": "Team strength",
    "season": "Season so far and form",
    "schedule": "Rest and travel",
    "roster": "Rotation quality",
    "availability": "Tonight's availability",
}

FEATURE_INFO = {
    "ELO_DIFF": ("Elo gap", "Difference in Elo ratings before the game, in points of expected margin"),
    "NO_CROWD": ("No home crowd", "Bubble or neutral-site game: no home advantage"),
    "REDUCED_CROWD": ("Reduced crowd", "2020-21, when arenas were empty or limited"),
    "NET_DIFF": ("Net rating gap", "Points per 100 possessions this season, pulled toward 0 early on"),
    "FORM_DIFF": ("Form gap", "Net rating over the last ten games, recent games weighted most"),
    "REST_DIFF": ("Rest gap", "Days since each team's last game (capped at 5)"),
    "HOME_B2B": ("Home on a back-to-back", "The home team played yesterday"),
    "AWAY_B2B": ("Away on a back-to-back", "The away team played yesterday"),
    "HOME_3IN4": ("Home 3rd game in 4 nights", ""),
    "AWAY_3IN4": ("Away 3rd game in 4 nights", ""),
    "AWAY_TRAVEL": ("Away travel", "Distance from the away team's previous game, in 1,000 km"),
    "AWAY_TZ_EAST": ("Away flew east", "Time zones the away team crossed eastward"),
    "FULL_DIFF": ("Full-strength roster gap", "Player value of each roster with everyone healthy"),
    "RECENT_DIFF": ("Recent lineup gap", "Player value of the lineups each team has fielded in its last ten"),
    "AVAIL_DIFF": (
        "Availability change",
        "Player value expected to play tonight minus what each team has fielded lately",
    ),
}


def win_probability(margin: float, spread: float) -> float:
    """P(final margin > 0) when the margin is normal around the prediction with this spread."""
    return 0.5 * (1 + math.erf(margin / (spread * math.sqrt(2))))


def capped_value(players: list[tuple[float, float, float]]) -> float:
    """
    Value above replacement a team can play from (rate, expected minutes, chance of playing) per
    player: minutes go to the best players first, up to 240 a game.
    """
    total = used = 0.0
    for rate, minutes, weight in sorted(players, key=lambda p: -p[0]):
        expected = minutes * weight
        total += rate * min(max(TEAM_MINUTES - used, 0.0), expected)
        used += expected
    return total


@dataclass(frozen=True)
class GameModel:
    features: list[str]
    groups: dict[str, list[str]]
    coefficients: dict[str, float]
    intercept: float
    spread: float
    play_rates: dict[str, float]
    trained_on: str

    @classmethod
    def from_json(cls, text: str) -> "GameModel":
        raw = json.loads(text)
        return cls(
            features=raw["features"], groups=raw["groups"], coefficients=raw["coefficients"],
            intercept=raw["intercept"], spread=raw["spread"], play_rates=raw["play_rates"],
            trained_on=raw["trained_on"],
        )

    def margin(self, features: dict[str, float]) -> float:
        return self.intercept + sum(features[f] * c for f, c in self.coefficients.items())

    def breakdown(self, features: dict[str, float]) -> list[dict]:
        """Points each group of inputs adds to the home team's margin; they sum to the prediction."""
        items = []
        # Home court first: it is where every game starts from
        for group, members in sorted(self.groups.items(), key=lambda item: item[0] != "home"):
            points = sum(features[f] * self.coefficients[f] for f in members)
            if group == "home":
                points += self.intercept  # the intercept is the home edge with a normal crowd
            items.append({"key": group, "label": GROUP_LABELS.get(group, group), "points": round(points, 2)})
        return items

    def describe(self) -> list[dict]:
        group_of = {f: g for g, members in self.groups.items() for f in members}
        return [
            {
                "name": f, "group": group_of[f], "label": FEATURE_INFO.get(f, (f, ""))[0],
                "description": FEATURE_INFO.get(f, (f, ""))[1], "coefficient": self.coefficients[f],
            }
            for f in self.features
        ]
