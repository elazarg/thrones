"""In-memory game store for loaded games."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.game import Game


class GameSummary(BaseModel):
    """Lightweight game summary for listings."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    players: list[str]
    version: str


class GameStore:
    """Simple in-memory store for loaded games."""

    def __init__(self) -> None:
        self._games: dict[str, Game] = {}

    def add(self, game: Game) -> str:
        """Add a game to the store. Returns game ID."""
        self._games[game.id] = game
        return game.id

    def get(self, game_id: str) -> Game | None:
        """Get a game by ID."""
        return self._games.get(game_id)

    def list(self) -> list[GameSummary]:
        """List all games as summaries."""
        return [
            GameSummary(
                id=g.id,
                title=g.title,
                players=g.players,
                version=g.version,
            )
            for g in self._games.values()
        ]

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
