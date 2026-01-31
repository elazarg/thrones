"""Gambit EFG text format model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EfgStringGame(BaseModel):
    """Game in Gambit's standard EFG text format.

    This is the industry-standard format used by Gambit, OpenSpiel, and other
    game theory tools. The efg_content field contains the actual EFG string.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    players: list[str]
    efg_content: str = Field(description="Gambit EFG text format string")
    tags: list[str] = Field(default_factory=list)
    format_name: Literal["efg"] = "efg"
