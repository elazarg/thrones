"""Shared helpers for analysis operations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.core.errors import incompatible_plugin, not_found

if TYPE_CHECKING:
    from app.core.registry import AnalysisPlugin
    from app.core.store import AnyGame, GameStore

logger = logging.getLogger(__name__)


def _find_compatible_game(
    store: GameStore,
    game: AnyGame,
    plugin: AnalysisPlugin,
) -> AnyGame | None:
    """Find a game format compatible with the plugin.

    Checks if the plugin can run on the native game, then tries conversions.

    Args:
        store: The game store (for conversions)
        game: The game to check/convert
        plugin: The analysis plugin

    Returns:
        Compatible game (native or converted) or None if no compatible format.
    """
    if plugin.can_run(game):
        return game

    applicable_formats = getattr(plugin, "applicable_to", [])

    for target_format in applicable_formats:
        if target_format == game.format_name:
            continue

        converted = store.get_converted(game.id, target_format)
        if converted and plugin.can_run(converted):
            logger.info(
                "Using %s conversion for analysis %s on game %s",
                target_format,
                plugin.name,
                game.id,
            )
            return converted

    return None


def resolve_game_for_plugin(
    store: GameStore,
    game_id: str,
    plugin: AnalysisPlugin,
) -> AnyGame:
    """Get game for analysis, converting if necessary.

    If the plugin cannot run on the game's native format, attempts to convert
    the game to formats listed in plugin.applicable_to.

    Args:
        store: The game store
        game_id: ID of the game to resolve
        plugin: The analysis plugin that will run on the game

    Returns:
        The game (possibly converted) that the plugin can run on.

    Raises:
        HTTPException 404: If game not found
        HTTPException 400: If no compatible format can be obtained
    """
    game = store.get(game_id)
    if game is None:
        raise not_found("Game", game_id)

    result = _find_compatible_game(store, game, plugin)
    if result is None:
        logger.warning(
            "Plugin '%s' cannot run on game %s (format: %s, applicable_to: %s)",
            plugin.name,
            game_id,
            game.format_name,
            getattr(plugin, "applicable_to", []),
        )
        raise incompatible_plugin(plugin.name, game.format_name)

    return result


def try_resolve_game_for_plugin(
    store: GameStore,
    game: AnyGame,
    plugin: AnalysisPlugin,
) -> AnyGame | None:
    """Try to get a compatible game for the plugin, returning None if not possible.

    Unlike resolve_game_for_plugin, this does not raise on incompatibility.

    Args:
        store: The game store
        game: The game to potentially convert
        plugin: The analysis plugin

    Returns:
        The game (possibly converted) or None if no compatible format exists.
    """
    return _find_compatible_game(store, game, plugin)
