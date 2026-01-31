"""Support Enumeration analysis.

Enumerates all possible support profiles (combinations of strategies
that might be played with positive probability) for a game.
Useful for understanding the structure of potential equilibria.
"""

from __future__ import annotations

from typing import Any

import pygambit as gbt
from pygambit.enumeration import SupportEnumeration

from gambit_plugin.gambit_utils import extensive_to_gambit_table, normal_form_to_gambit
from gambit_plugin.strategies import enumerate_strategies, resolve_payoffs


def run_support_enum(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Enumerate all possible support profiles for a game.

    A support profile specifies which strategies each player might
    use with positive probability. This analysis lists all such
    combinations that could potentially be part of a Nash equilibrium.

    Args:
        game: Deserialized game dict (extensive or normal form).
        config: Optional config (currently unused).

    Returns:
        Dict with 'summary' and 'details' keys. Details contains
        'supports' listing each support profile.
    """
    config = config or {}
    format_name = game.get("format_name", "extensive")

    # Convert to Gambit game
    if format_name == "normal":
        gambit_game = normal_form_to_gambit(game)
    else:
        strategies = enumerate_strategies(game)
        gambit_game = extensive_to_gambit_table(game, strategies, resolve_payoffs)

    try:
        enumerator = SupportEnumeration()
        supports = list(enumerator.enumerate_supports(gambit_game))

        # Convert to serializable format
        support_list = []
        for support in supports:
            support_dict = _support_to_dict(gambit_game, support)
            support_list.append(support_dict)

        count = len(support_list)
        summary = f"{count} possible support profile{'s' if count != 1 else ''}"

        return {
            "summary": summary,
            "details": {
                "supports": support_list,
                "count": count,
                "solver": "gambit-support-enum",
            },
        }

    except (ValueError, IndexError, RuntimeError, TypeError) as e:
        return {
            "summary": f"Support enumeration failed: {e}",
            "details": {
                "supports": [],
                "solver": "gambit-support-enum",
                "error": str(e),
            },
        }


def _support_to_dict(game: gbt.Game, support) -> dict[str, Any]:
    """Convert a support profile to a serializable dict."""
    result: dict[str, list[str]] = {}

    # Support is indexed by player
    for player in game.players:
        player_support = []
        for strategy in player.strategies:
            # Check if strategy is in support
            try:
                if support[strategy]:
                    player_support.append(strategy.label)
            except (KeyError, TypeError):
                # If we can't check, assume it's in support
                player_support.append(strategy.label)
        result[player.label] = player_support

    # Create a description
    desc_parts = []
    for player, strats in result.items():
        if len(strats) == 1:
            desc_parts.append(f"{player}: {strats[0]}")
        else:
            desc_parts.append(f"{player}: {{{', '.join(strats)}}}")

    return {
        "description": " | ".join(desc_parts),
        "support": result,
    }
