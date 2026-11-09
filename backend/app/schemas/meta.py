from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import PlayerRef, Season, TeamRef


class NextGameModelInfo(BaseModel):
    test_season: Season
    test_games: int
    accuracy: float
    home_baseline: float = Field(description="Accuracy of always picking the home team")
    record_baseline: float = Field(description="Accuracy of picking the team with the better record")


class MvpModelInfo(BaseModel):
    correct: int
    seasons: int


class Meta(BaseModel):
    first_season: Season
    last_season: Season
    built_at: str
    mvp_model: MvpModelInfo
    next_game_model: NextGameModelInfo


class SeasonInfo(BaseModel):
    season: Season
    champion: TeamRef | None
    mvp: PlayerRef | None


class Health(BaseModel):
    status: Literal["ok"]
    schema_version: int
    built_at: str
