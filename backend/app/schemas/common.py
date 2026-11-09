"""Shared response models. Stat fields ending in _pg are per-game; *_pct fields are fractions (0.512 = 51.2%)."""
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

SEASON_PATTERN = r"^\d{4}-\d{2}$"
Season = str  # e.g. "2023-24"; validated with SEASON_PATTERN where it is user input
PositionGroup = Literal["G", "F", "C"]
Archetype = Literal["Scorer", "Playmaker", "Rebounder", "Defensive Player"]
Tier = Literal["Elite", "Very Good", "Average"]


class ErrorResponse(BaseModel):
    detail: str = Field(examples=["Player 123 not found"])


class TeamRef(BaseModel):
    abbr: str = Field(examples=["OKC"])
    name: str = Field(examples=["Oklahoma City Thunder"])
    primary_color: str = Field(examples=["#007AC1"])
    secondary_color: str
    logo_url: str


class PlayerRef(BaseModel):
    id: int
    name: str
    position_group: PositionGroup
    headshot_url: str


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(description="Total matching items, ignoring limit/offset")
    limit: int
    offset: int
