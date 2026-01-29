"""In-memory game store for loaded games."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import AnyGame

if TYPE_CHECKING:
    from app.conversions.registry import ConversionRegistry

logger = logging.getLogger(__name__)


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
    description: str | None = None
    players: list[str]
    format: Literal["extensive", "normal", "maid"] = "extensive"
    tags: list[str] = Field(default_factory=list)
    conversions: dict[str, ConversionInfo] = Field(default_factory=dict)


class GameStore:
    """Thread-safe in-memory store for loaded games.

    Automatically pre-computes conversions in the background when games are added.
    """

    def __init__(self, precompute_conversions: bool = True) -> None:
        self._games: dict[str, AnyGame] = {}
        self._conversions: dict[tuple[str, str], AnyGame] = {}  # (game_id, format) -> converted game
        self._lock = Lock()
        self._precompute = precompute_conversions
        self._executor: ThreadPoolExecutor | None = None
        self._executor_lock = Lock()

    def _get_executor(self) -> ThreadPoolExecutor:
        """Get or create the background executor for conversions."""
        with self._executor_lock:
            if self._executor is None or getattr(self._executor, "_shutdown", False):
                # Use a small pool - conversions are CPU-bound
                self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="conversion")
            return self._executor

    def _get_conversion_registry(self) -> "ConversionRegistry":
        """Get the conversion registry (lazy import to avoid circular deps)."""
        from app.dependencies import get_conversion_registry
        return get_conversion_registry()

    def add(self, game: AnyGame) -> str:
        """Add a game to the store. Returns game ID.

        Triggers background pre-computation of all possible conversions.
        """
        with self._lock:
            self._games[game.id] = game
            # Invalidate any cached conversions for this game
            self._invalidate_conversions_unlocked(game.id)

        # Pre-compute conversions in background
        if self._precompute:
            self._schedule_conversions(game)

        return game.id

    def _schedule_conversions(self, game: AnyGame) -> None:
        """Schedule background conversion tasks for a game."""
        try:
            conversion_reg = self._get_conversion_registry()
            available = conversion_reg.available_conversions(game)

            for target_format, check in available.items():
                if check.possible:
                    self._get_executor().submit(
                        self._precompute_conversion,
                        game.id,
                        target_format,
                    )
        except Exception as e:
            # Don't fail the add() call if scheduling fails
            logger.warning("Failed to schedule conversions for %s: %s", game.id, e)

    def _precompute_conversion(self, game_id: str, target_format: str) -> None:
        """Background task to pre-compute a conversion."""
        try:
            # Check if game still exists and conversion not already cached
            with self._lock:
                if game_id not in self._games:
                    return
                cache_key = (game_id, target_format)
                if cache_key in self._conversions:
                    return
                game = self._games[game_id]

            # Perform conversion outside lock
            conversion_reg = self._get_conversion_registry()
            check = conversion_reg.check(game, target_format)
            if not check.possible:
                return

            converted = conversion_reg.convert(game, target_format)

            # Cache the result (check game still exists)
            with self._lock:
                if game_id in self._games:
                    self._conversions[(game_id, target_format)] = converted
                    logger.debug(
                        "Pre-computed conversion: %s -> %s",
                        game_id,
                        target_format,
                    )
        except Exception as e:
            # Log but don't fail - conversion will happen on-demand if needed
            logger.debug(
                "Background conversion failed (%s -> %s): %s",
                game_id,
                target_format,
                e,
            )

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
        """List all games as lightweight summaries (no conversion info)."""
        with self._lock:
            games_copy = list(self._games.values())

        return [
            GameSummary(
                id=game.id,
                title=game.title,
                description=game.description,
                players=list(game.players),
                format=game.format_name,
                tags=list(game.tags),
            )
            for game in games_copy
        ]

    def get_summary(self, game_id: str) -> GameSummary | None:
        """Get a full game summary including conversion info."""
        with self._lock:
            game = self._games.get(game_id)
            if game is None:
                return None

        conversion_reg = self._get_conversion_registry()
        raw_conversions = conversion_reg.available_conversions(game)
        conversions = {
            target: ConversionInfo(
                possible=check.possible,
                warnings=check.warnings,
                blockers=check.blockers,
            )
            for target, check in raw_conversions.items()
        }

        return GameSummary(
            id=game.id,
            title=game.title,
            description=game.description,
            players=list(game.players),
            format=game.format_name,
            tags=list(game.tags),
            conversions=conversions,
        )

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
        conversion_reg = self._get_conversion_registry()
        check = conversion_reg.check(game, target_format)
        if not check.possible:
            return None

        converted = conversion_reg.convert(game, target_format)

        # Cache the result
        with self._lock:
            if game_id in self._games:
                self._conversions[cache_key] = converted
        return converted

    def is_conversion_ready(self, game_id: str, target_format: str) -> bool:
        """Check if a conversion is already cached (ready for instant access)."""
        with self._lock:
            game = self._games.get(game_id)
            if game is None:
                return False
            if game.format_name == target_format:
                return True
            return (game_id, target_format) in self._conversions

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

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the background executor."""
        with self._executor_lock:
            if self._executor is not None:
                self._executor.shutdown(wait=wait, cancel_futures=True)
                self._executor = None

    def __len__(self) -> int:
        with self._lock:
            return len(self._games)

    def __contains__(self, game_id: str) -> bool:
        with self._lock:
            return game_id in self._games
