"""Vegas game model - source code format.

Vegas games are stored as source code and converted to MAID/EFG/NFG
for analysis, similar to how EFG/NFG can be converted between each other.
"""
from __future__ import annotations
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VegasGame(BaseModel):
    """Vegas DSL game stored as source code.

    This is a "source format" - the game is defined by its Vegas source code.
    Conversions to MAID, EFG, NFG happen asynchronously via the Vegas plugin.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    description: str | None = None
    source_code: str  # The Vegas .vg source code
    # Players extracted from source (for display in game list)
    players: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    format_name: Literal["vegas"] = "vegas"
