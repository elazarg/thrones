"""In-memory game store for loaded games."""
from __future__ import annotations

from typing import Union

from pydantic import BaseModel, ConfigDict

from app.models.game import Game
from app.models.normal_form import NormalFormGame

# Union type for any game representation
AnyGame = Union[Game, NormalFormGame]


class GameSummary(BaseModel):
    """Lightweight game summary for listings."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    players: list[str]
    version: str
    format: str = "extensive"  # "extensive" or "normal"


class GameStore:
    """Simple in-memory store for loaded games."""

    def __init__(self) -> None:
        self._games: dict[str, AnyGame] = {}

    def add(self, game: AnyGame) -> str:
        """Add a game to the store. Returns game ID."""
        self._games[game.id] = game
        return game.id

    def get(self, game_id: str) -> AnyGame | None:
        """Get a game by ID."""
        return self._games.get(game_id)

    def get_format(self, game_id: str) -> str | None:
        """Get the format of a game ('extensive' or 'normal')."""
        game = self._games.get(game_id)
        if game is None:
            return None
        return "normal" if isinstance(game, NormalFormGame) else "extensive"

    def list(self) -> list[GameSummary]:
        """List all games as summaries."""
        summaries = []
        for g in self._games.values():
            fmt = "normal" if isinstance(g, NormalFormGame) else "extensive"
            summaries.append(
                GameSummary(
                    id=g.id,
                    title=g.title,
                    players=list(g.players),
                    version=g.version,
                    format=fmt,
                )
            )
        return summaries

    def remove(self, game_id: str) -> bool:
        """Remove a game. Returns True if game existed."""
        if game_id in self._games:
            del self._games[game_id]
            return True
        return False

    def clear(self) -> None:
        """Remove all games."""
        self._games.clear()

    def __len__(self) -> int:
        return len(self._games)

    def __contains__(self, game_id: str) -> bool:
        return game_id in self._games


# Global store instance
game_store = GameStore()
