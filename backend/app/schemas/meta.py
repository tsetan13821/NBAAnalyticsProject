from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import PlayerRef, Season, TeamRef


class GameModelInfo(BaseModel):
    train_first_season: Season
    train_last_season: Season
    train_games: int
    test_season: Season = Field(description="Held out: the model never saw these games while training")
    test_games: int
    accuracy: float
    log_loss: float
    home_baseline: float = Field(description="Accuracy of always picking the home team")
    record_baseline: float = Field(description="Accuracy of picking the team with the better record")
    elo_baseline: float = Field(description="Accuracy of Elo ratings alone")


class GameSeasonInfo(BaseModel):
    season: Season
    as_of: str = Field(description="When the predictions were made (ISO, Eastern)")
    games_played: int
    correct: int = Field(description="Played games whose favourite won")
    upcoming_games: int


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
    game_model: GameModelInfo
    game_season: GameSeasonInfo | None = Field(description="The game model on the season in progress")


class SeasonInfo(BaseModel):
    season: Season
    in_progress: bool = Field(description="True for the season under way: the numbers are so far, not final")
    champion: TeamRef | None
    mvp: PlayerRef | None


class Health(BaseModel):
    status: Literal["ok"]
    schema_version: int
    built_at: str
