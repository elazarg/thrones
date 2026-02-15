"""Strategy enumeration and payoff resolution for Pydantic game models.

This module provides wrappers around the shared.strategies module,
converting Pydantic ExtensiveFormGame models to dicts for processing.

For the underlying algorithms, see shared-pkg/shared/strategies.py.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import TYPE_CHECKING

from shared import strategies as shared_strategies

if TYPE_CHECKING:
    from app.models import ExtensiveFormGame


def _game_to_dict(game: ExtensiveFormGame) -> dict:
    """Convert a Pydantic game model to a plain dict for shared utilities."""
    return game.model_dump()


def iter_strategies(
    game: ExtensiveFormGame,
    player: str,
) -> Iterator[dict[str, str]]:
    """Lazily enumerate all pure strategies for a player.

    This generator yields strategies one at a time, allowing early termination
    if not all strategies are needed.

    Args:
        game: The extensive-form game.
        player: The player whose strategies to enumerate.

    Yields:
        Strategy dicts mapping node_id -> action_label.
    """
    game_dict = _game_to_dict(game)
    yield from shared_strategies.iter_strategies(game_dict, player)


def enumerate_strategies(
    game: ExtensiveFormGame,
) -> dict[str, list[Mapping[str, str]]]:
    """Enumerate all pure strategies for each player.

    A strategy is a complete plan: one action for each information set.

    Args:
        game: The extensive-form game.

    Returns:
        Dict mapping player name to list of strategies.
        Each strategy maps node_id -> action_label.
    """
    game_dict = _game_to_dict(game)
    return shared_strategies.all_strategies(game_dict)


def estimate_strategy_count(game: ExtensiveFormGame) -> int:
    """Estimate total strategy profile count WITHOUT enumerating.

    This is O(nodes) instead of O(product of all action counts).

    Args:
        game: The extensive-form game.

    Returns:
        Estimated total number of strategy profiles (capped at 10M).
    """
    game_dict = _game_to_dict(game)
    return shared_strategies.estimate_strategy_count(game_dict)


def resolve_payoffs(
    game: ExtensiveFormGame,
    profile: Mapping[str, Mapping[str, str]],
) -> dict[str, float]:
    """Simulate a strategy profile to get terminal payoffs for all players.

    Args:
        game: The extensive-form game.
        profile: Maps player name -> (node_id -> action_label).

    Returns:
        Dict mapping player name to payoff.

    Raises:
        ValueError: If profile is invalid or no terminal outcome reached.
    """
    game_dict = _game_to_dict(game)
    return shared_strategies.resolve_payoffs(game_dict, profile)


def resolve_payoff(
    game: ExtensiveFormGame,
    player: str,
    profile: Mapping[str, Mapping[str, str]],
) -> float:
    """Resolve the payoff for a single player given a strategy profile.

    Args:
        game: The extensive-form game.
        player: The player whose payoff to return.
        profile: Maps player name -> (node_id -> action_label).

    Returns:
        The payoff for the specified player.

    Raises:
        ValueError: If profile is invalid or no terminal outcome reached.
    """
    game_dict = _game_to_dict(game)
    return shared_strategies.resolve_payoff(game_dict, player, profile)
