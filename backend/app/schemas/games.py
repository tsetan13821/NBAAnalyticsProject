from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import Season, TeamRef

WinPct = Field(default=None, ge=0, le=1)


class PredictionRequest(BaseModel):
    """Predict a game. Any win % left out defaults to the team's record in the latest season."""

    home_team: str = Field(min_length=2, max_length=3, examples=["BOS"])
    away_team: str = Field(min_length=2, max_length=3, examples=["DAL"])
    home_win_pct: float | None = WinPct
    home_home_win_pct: float | None = WinPct
    away_win_pct: float | None = WinPct
    away_road_win_pct: float | None = WinPct

    @model_validator(mode="after")
    def different_teams(self) -> Self:
        if self.home_team.upper() == self.away_team.upper():
            raise ValueError("home_team and away_team must be different")
        return self


class PredictionInputs(BaseModel):
    home_win_pct: float
    home_home_win_pct: float
    away_win_pct: float
    away_road_win_pct: float
    defaults_from_season: Season = Field(description="Season whose final records filled any omitted inputs")


class Prediction(BaseModel):
    home_team: TeamRef
    away_team: TeamRef
    inputs: PredictionInputs
    home_win_probability: float
    away_win_probability: float
    favorite: str
