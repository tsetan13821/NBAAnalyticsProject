"""Game predictions for the season in progress. Margins are the home team's, in points."""
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Page, Season, TeamRef

InjuryStatus = Literal["Out", "Doubtful", "Questionable", "Probable", "Available"]


class TeamSide(BaseModel):
    team: TeamRef
    wins: int = Field(description="Record before the game")
    losses: int
    elo: float = Field(description="Elo rating before the game (league average 1500)")


class GameResult(BaseModel):
    home_pts: int
    away_pts: int
    winner: str = Field(examples=["BOS"])
    correct: bool = Field(description="The model's favourite won")


class Absence(BaseModel):
    player_id: int
    name: str
    team_abbr: str
    status: InjuryStatus
    value_lost: float = Field(description="Player value (points of Game Score) the team expects to be without")
    already_missing: bool = Field(
        description="He has missed most of the team's last ten games, so the team's recent results already "
        "reflect his absence and it barely moves the prediction"
    )


class GameSummary(BaseModel):
    game_id: str
    season: Season
    date: str = Field(description="ISO date, US Eastern")
    tip_et: str | None = Field(description="Tip-off, 'HH:MM' Eastern (upcoming games)")
    home: TeamSide
    away: TeamSide
    home_win_probability: float
    predicted_margin: float = Field(description="Home team's predicted margin; negative favours the away team")
    favorite: str
    result: GameResult | None = Field(description="Final score, once played")
    key_absences: list[Absence] = Field(
        description="Players listed Out, Doubtful or Questionable who are worth the most to their team, at most four"
    )


class BreakdownItem(BaseModel):
    key: str = Field(examples=["availability"])
    label: str = Field(examples=["Tonight's availability"])
    points: float = Field(description="Points this group adds to the home team's margin")


class GamePlayer(BaseModel):
    id: int
    name: str
    headshot_url: str
    team_abbr: str
    value: float = Field(description="Game Score above a replacement player at his usual minutes")
    expected_minutes: float
    participation: float = Field(description="Share of the team's last ten games he played")
    status: InjuryStatus | None = Field(description="Injury report status; NULL when not listed")
    reason: str | None
    status_source: Literal["report", "carried"] | None = Field(
        description="'carried': no report covers this game yet, so his latest status is carried forward"
    )
    chance: float = Field(description="Chance of playing the prediction uses (after any what-if)")
    played: bool | None = Field(description="Whether he played, once the game is over")
    what_if: Literal["out", "in"] | None = Field(description="Set when this request changed his chance")


class WhatIf(BaseModel):
    out: list[int]
    in_: list[int] = Field(alias="in")
    base_home_win_probability: float = Field(description="Before the changes")
    base_predicted_margin: float


class GameDetail(GameSummary):
    breakdown: list[BreakdownItem] = Field(description="Sums to predicted_margin")
    spread: float = Field(description="Standard deviation of the real margin around the prediction")
    home_players: list[GamePlayer] = Field(description="Most valuable first")
    away_players: list[GamePlayer]
    what_if: WhatIf | None


class UpcomingGames(BaseModel):
    season: Season | None
    as_of: str | None = Field(description="When the predictions were made (ISO, Eastern)")
    injury_report: str | None = Field(description="Time of the injury report they use (ISO, Eastern)")
    games: list[GameSummary]


class ConfidenceBin(BaseModel):
    low: float = Field(description="The favourite's predicted chance, from")
    high: float
    games: int
    favorite_won: int
    predicted: float = Field(description="Average predicted chance of the favourite")


class TrackRecord(BaseModel):
    season: Season | None
    games: int
    correct: int
    accuracy: float | None
    log_loss: float | None
    brier: float | None
    home_team_won: float | None = Field(description="Share of games the home team won (a baseline)")
    by_confidence: list[ConfidenceBin]


class GameResults(Page[GameSummary]):
    record: TrackRecord


class FeatureInfo(BaseModel):
    name: str
    group: str
    label: str
    description: str
    coefficient: float = Field(description="Points of margin per unit")


class Scores(BaseModel):
    accuracy: float
    log_loss: float
    brier: float


class HeldOut(Scores):
    margin_mae: float = Field(description="Mean absolute error of the predicted margin, points")


class Baselines(BaseModel):
    home_team: float = Field(description="Accuracy of always picking the home team")
    better_record: float = Field(description="Accuracy of picking the team with the better record so far")
    elo: Scores


class AblationStep(Scores):
    added: str


class CalibrationBin(BaseModel):
    low: float = Field(description="The favourite's predicted chance, from")
    high: float
    games: int
    predicted: float
    actual: float = Field(description="Share of these games the favourite won")


class WalkForwardSeason(Scores):
    season: Season
    train_games: int
    test_games: int
    baselines: Baselines


class Evaluation(BaseModel):
    train_first_season: Season
    train_last_season: Season
    train_games: int
    test_season: Season
    test_games: int
    held_out: HeldOut
    baselines: Baselines
    models: dict[str, Scores] = Field(description="Alternatives scored on the same games")
    ablation: list[AblationStep] = Field(description="Input groups added one at a time")
    calibration: list[CalibrationBin]
    walk_forward: list[WalkForwardSeason]


class GameModelDetails(BaseModel):
    trained_on: str = Field(examples=["2019-20 to 2025-26"])
    intercept: float = Field(description="Home edge with a normal crowd, points")
    spread: float
    play_rates: dict[str, float] = Field(description="Share of listed players who played, by status")
    features: list[FeatureInfo]
    evaluation: Evaluation
