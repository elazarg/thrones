"""Cognitive Hierarchy / Level-K analysis.

Models strategic thinking where players reason about others' behavior
at different levels of sophistication:
- Level-0: Random play
- Level-1: Best responds to Level-0
- Level-2: Best responds to mix of Level-0 and Level-1
- etc.
"""

from __future__ import annotations

from typing import Any

import pygambit as gbt
import pygambit.levelk as levelk

from gambit_plugin.gambit_utils import extensive_to_gambit_table, normal_form_to_gambit
from gambit_plugin.strategies import enumerate_strategies, resolve_payoffs


def run_levelk(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compute Cognitive Hierarchy predictions for a game.

    The Cognitive Hierarchy model assumes players have different levels
    of strategic thinking, with a Poisson distribution of types.

    Args:
        game: Deserialized game dict (extensive or normal form).
        config: Optional config with 'tau' (Poisson parameter, default 1.5),
                'max_level' (maximum level to compute, default 10).

    Returns:
        Dict with 'summary' and 'details' keys. Details contains
        'levels' with behavior at each level of reasoning.
    """
    config = config or {}
    tau = config.get("tau", 1.5)  # Poisson parameter for level distribution
    max_level = config.get("max_level", 10)
    format_name = game.get("format_name", "extensive")

    # Convert to Gambit game
    if format_name == "normal":
        gambit_game = normal_form_to_gambit(game)
    else:
        strategies = enumerate_strategies(game)
        gambit_game = extensive_to_gambit_table(game, strategies, resolve_payoffs)

    try:
        # Compute cognitive hierarchy
        ch_result = levelk.compute_coghier(gambit_game, tau=tau)

        # Extract the aggregate prediction
        aggregate = _profile_to_dict(gambit_game, ch_result)
        aggregate["description"] = f"Cognitive Hierarchy (τ={tau})"

        return {
            "summary": f"Cognitive Hierarchy prediction (τ={tau})",
            "details": {
                "equilibria": [aggregate],
                "tau": tau,
                "solver": "gambit-coghier",
            },
        }

    except (ValueError, IndexError, RuntimeError, TypeError) as e:
        return {
            "summary": f"Cognitive Hierarchy computation failed: {e}",
            "details": {
                "levels": [],
                "tau": tau,
                "solver": "gambit-coghier",
                "error": str(e),
            },
        }


def _clean_float(value: float, tolerance: float = 1e-6) -> float:
    """Round floats and snap to common rational values."""
    if abs(value) < tolerance:
        return 0.0

    common_fractions = [0.5, 1 / 3, 2 / 3, 0.25, 0.75]
    for frac in common_fractions:
        if abs(value - frac) < tolerance:
            return frac

    return round(value, 6)


def _profile_to_dict(game: gbt.Game, profile) -> dict[str, Any]:
    """Convert a Gambit profile to a serializable dict."""
    strategies: dict[str, dict[str, float]] = {}

    # CognitiveHierarchyProfile is iterable like a mixed strategy profile
    for player in game.players:
        player_strategies = {}
        for strategy in player.strategies:
            prob = float(profile[strategy])
            player_strategies[strategy.label] = _clean_float(prob)
        strategies[player.label] = player_strategies

    # Compute expected payoffs
    payoffs = {}
    for player in game.players:
        try:
            payoffs[player.label] = _clean_float(float(profile.payoff(player)))
        except (AttributeError, TypeError):
            # If payoff method not available, skip
            payoffs[player.label] = 0.0

    return {
        "description": "Level-K prediction",
        "behavior_profile": strategies,
        "strategies": strategies,
        "payoffs": payoffs,
    }
