"""In-memory game store for loaded games."""
from __future__ import annotations
from threading import Lock
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.conversions import conversion_registry
from app.models import AnyGame


def is_supported_format(format_name: str) -> bool:
    """Check if the format name is supported."""
    return format_name in ("extensive", "normal", "maid")


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
    format: Literal["extensive", "normal", "maid"] = "extensive"
    conversions: dict[str, ConversionInfo] = Field(default_factory=dict)


class GameStore:
    """Thread-safe in-memory store for loaded games."""

    def __init__(self) -> None:
        self._games: dict[str, AnyGame] = {}
        self._conversions: dict[tuple[str, str], AnyGame] = {}  # (game_id, format) -> converted game
        self._lock = Lock()

    def add(self, game: AnyGame) -> str:
        """Add a game to the store. Returns game ID."""
        with self._lock:
            self._games[game.id] = game
            # Invalidate any cached conversions for this game
            self._invalidate_conversions_unlocked(game.id)
        return game.id

    def _invalidate_conversions_unlocked(self, game_id: str) -> None:
        """Remove cached conversions for a game. Caller must hold _lock."""
        keys_to_remove = [k for k in self._conversions if k[0] == game_id]
        for key in keys_to_remove:
            del self._conversions[key]

    def get(self, game_id: str) -> AnyGame | None:
        """Get a game by ID."""
        with self._lock:
            return self._games.get(game_id)

    def get_format(self, game_id: str) -> str | None:
        """Get the format of a game ('extensive' or 'normal')."""
        with self._lock:
            game = self._games.get(game_id)
            if game is None:
                return None
            return game.format_name

    def list(self) -> list[GameSummary]:
        """List all games as summaries."""
        with self._lock:
            games_copy = list(self._games.values())

        # Build summaries outside the lock (conversion_registry has its own locking if needed)
        summaries = []
        for game in games_copy:
            # Get available conversions
            raw_conversions = conversion_registry.available_conversions(game)
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
                    id=game.id,
                    title=game.title,
                    players=list(game.players),
                    version=game.version,
                    format=game.format_name,
                    conversions=conversions,
                )
            )
        return summaries

    def get_converted(self, game_id: str, target_format: str) -> AnyGame | None:
        """Get a game converted to the target format (cached)."""
        with self._lock:
            game = self._games.get(game_id)
            if game is None:
                return None

            # Check if already in target format
            current_format = game.format_name
            if current_format == target_format:
                return game

            # Check cache
            cache_key = (game_id, target_format)
            if cache_key in self._conversions:
                return self._conversions[cache_key]

        # Perform conversion outside lock (may be expensive)
        check = conversion_registry.check(game, target_format)
        if not check.possible:
            return None

        converted = conversion_registry.convert(game, target_format)

        # Cache the result
        with self._lock:
            self._conversions[cache_key] = converted
        return converted

    def remove(self, game_id: str) -> bool:
        """Remove a game. Returns True if game existed."""
        with self._lock:
            if game_id in self._games:
                del self._games[game_id]
                self._invalidate_conversions_unlocked(game_id)
                return True
            return False

    def clear(self) -> None:
        """Remove all games."""
        with self._lock:
            self._games.clear()
            self._conversions.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._games)

    def __contains__(self, game_id: str) -> bool:
        with self._lock:
            return game_id in self._games


# Global store instance
game_store = GameStore()
