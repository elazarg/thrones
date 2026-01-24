"""In-memory game store for loaded games."""
from __future__ import annotations

from typing import Union

from pydantic import BaseModel, ConfigDict, Field

from app.models.game import Game
from app.models.normal_form import NormalFormGame
from app.conversions import conversion_registry

# Union type for any game representation
AnyGame = Union[Game, NormalFormGame]


class ConversionInfo(BaseModel):
    """Information about a possible conversion."""

    model_config = ConfigDict(frozen=True)

    possible: bool
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class GameSummary(BaseModel):
    """Lightweight game summary for listings."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    players: list[str]
    version: str
    format: str = "extensive"  # "extensive" or "normal"
    conversions: dict[str, ConversionInfo] = Field(default_factory=dict)


class GameStore:
    """Simple in-memory store for loaded games."""

    def __init__(self) -> None:
        self._games: dict[str, AnyGame] = {}
        self._conversions: dict[tuple[str, str], AnyGame] = {}  # (game_id, format) -> converted game

    def add(self, game: AnyGame) -> str:
        """Add a game to the store. Returns game ID."""
        self._games[game.id] = game
        # Invalidate any cached conversions for this game
        self._invalidate_conversions(game.id)
        return game.id

    def _invalidate_conversions(self, game_id: str) -> None:
        """Remove cached conversions for a game."""
        keys_to_remove = [k for k in self._conversions if k[0] == game_id]
        for key in keys_to_remove:
            del self._conversions[key]

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

            # Get available conversions
            raw_conversions = conversion_registry.available_conversions(g)
            conversions = {
                target: ConversionInfo(
                    possible=check.possible,
                    warnings=check.warnings,
                    blockers=check.blockers,
                )
                for target, check in raw_conversions.items()
            }

            summaries.append(
                GameSummary(
                    id=g.id,
                    title=g.title,
                    players=list(g.players),
                    version=g.version,
                    format=fmt,
                    conversions=conversions,
                )
            )
        return summaries

    def get_converted(self, game_id: str, target_format: str) -> AnyGame | None:
        """Get a game converted to the target format (cached)."""
        game = self._games.get(game_id)
        if game is None:
            return None

        # Check if already in target format
        current_format = "normal" if isinstance(game, NormalFormGame) else "extensive"
        if current_format == target_format:
            return game

        # Check cache
        cache_key = (game_id, target_format)
        if cache_key in self._conversions:
            return self._conversions[cache_key]

        # Perform conversion
        check = conversion_registry.check(game, target_format)
        if not check.possible:
            return None

        converted = conversion_registry.convert(game, target_format)
        self._conversions[cache_key] = converted
        return converted

    def remove(self, game_id: str) -> bool:
        """Remove a game. Returns True if game existed."""
        if game_id in self._games:
            del self._games[game_id]
            self._invalidate_conversions(game_id)
            return True
        return False

    def clear(self) -> None:
        """Remove all games."""
        self._games.clear()
        self._conversions.clear()

    def __len__(self) -> int:
        return len(self._games)

    def __contains__(self, game_id: str) -> bool:
        return game_id in self._games


# Global store instance
game_store = GameStore()
