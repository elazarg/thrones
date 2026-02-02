"""Normal form (strategic form) game model.

Represents games as a payoff matrix rather than a tree.
Used for 2-player simultaneous games.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NormalFormGame(BaseModel):
    """Strategic form game represented as a payoff matrix.

    For 2-player games:
    - Player 1 (row player) chooses from `strategies[0]`
    - Player 2 (column player) chooses from `strategies[1]`
    - `payoffs[i][j]` gives payoffs when P1 plays strategy i, P2 plays strategy j
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    description: str | None = None
    players: tuple[str, str]  # Exactly 2 players
    strategies: tuple[list[str], list[str]]  # Strategies per player
    payoffs: list[list[tuple[float, float]]]  # [row][col] -> (P1 payoff, P2 payoff)
    tags: list[str] = Field(default_factory=list)
    format_name: Literal["normal"] = "normal"
    # Mapping from MAID decision node ID to player name (present when converted from MAID)
    maid_decision_to_player: dict[str, str] | None = None

    @property
    def num_strategies(self) -> tuple[int, int]:
        """Return number of strategies for each player."""
        return (len(self.strategies[0]), len(self.strategies[1]))

    def get_payoff(self, row: int, col: int) -> tuple[float, float]:
        """Get payoffs for a strategy profile."""
        return self.payoffs[row][col]

    def row_player_payoff(self, row: int, col: int) -> float:
        """Get row player (P1) payoff."""
        return self.payoffs[row][col][0]

    def col_player_payoff(self, row: int, col: int) -> float:
        """Get column player (P2) payoff."""
        return self.payoffs[row][col][1]
