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
    current_season: Season | None = Field(
        description="The season under way, if its stats so far are included; last_season is the last completed one"
    )
    current_season_as_of: str | None = Field(description="Date (YYYY-MM-DD) the season-in-progress stats were fetched")
    rosters_as_of: str = Field(description="Date (YYYY-MM-DD) the current-team data was taken from NBA.com rosters")
    mvp_model: MvpModelInfo
    next_game_model: NextGameModelInfo


class SeasonInfo(BaseModel):
    season: Season
    in_progress: bool = Field(description="True for the season under way: the numbers are so far, not final")
    champion: TeamRef | None
    mvp: PlayerRef | None


class Health(BaseModel):
    status: Literal["ok"]
    schema_version: int
    built_at: str
