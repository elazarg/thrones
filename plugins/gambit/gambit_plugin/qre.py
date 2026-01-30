"""Quantal Response Equilibrium (QRE) analysis.

QRE models bounded rationality by allowing agents to make errors
proportional to the cost of those errors. As lambda (rationality)
increases, behavior converges to Nash equilibrium.
"""
from __future__ import annotations

from typing import Any

import pygambit as gbt

from gambit_plugin.gambit_utils import extensive_to_gambit_table, normal_form_to_gambit
from gambit_plugin.strategies import enumerate_strategies, resolve_payoffs


def run_qre(game: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compute Quantal Response Equilibrium path for a game.

    Returns a sequence of equilibria along the QRE correspondence,
    from uniform random play (lambda=0) toward Nash equilibrium (lambda→∞).

    Args:
        game: Deserialized game dict (extensive or normal form).
        config: Optional config with 'first_step', 'max_accel' keys.

    Returns:
        Dict with 'summary' and 'details' keys. Details contains 'path'
        with equilibria at different lambda (rationality) values.
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
        # Use logit_solve which returns the QRE at the end of the principal branch
        result = gbt.nash.logit_solve(gambit_game)

        # Get the equilibrium
        if not result.equilibria:
            return {
                "summary": "No QRE found",
                "details": {"path": [], "solver": "gambit-logit"},
            }

        # Convert the final equilibrium
        eq = result.equilibria[0]
        final_eq = _profile_to_dict(gambit_game, eq)

        return {
            "summary": f"QRE computed (1 equilibrium at high rationality)",
            "details": {
                "equilibria": [final_eq],
                "path": [final_eq],  # Single point for now
                "solver": "gambit-logit",
            },
        }

    except (ValueError, IndexError, RuntimeError) as e:
        return {
            "summary": f"QRE computation failed: {e}",
            "details": {"path": [], "solver": "gambit-logit", "error": str(e)},
        }


def _clean_float(value: float, tolerance: float = 1e-6) -> float:
    """Round floats and snap to common rational values."""
    if abs(value) < tolerance:
        return 0.0

    common_fractions = [0.5, 1/3, 2/3, 0.25, 0.75]
    for frac in common_fractions:
        if abs(value - frac) < tolerance:
            return frac

    return round(value, 6)


def _profile_to_dict(game: gbt.Game, eq) -> dict[str, Any]:
    """Convert a Gambit equilibrium to a serializable dict."""
    strategies: dict[str, dict[str, float]] = {}
    for strategy, probability in eq:
        player_label = strategy.player.label
        strategies.setdefault(player_label, {})[strategy.label] = _clean_float(float(probability))

    payoffs = {player.label: _clean_float(float(eq.payoff(player))) for player in game.players}

    pure = all(p in (0.0, 1.0) for probs in strategies.values() for p in probs.values())
    description = "Pure strategy QRE" if pure else "Mixed strategy QRE"

    return {
        "description": description,
        "behavior_profile": strategies,
        "strategies": strategies,
        "payoffs": payoffs,
    }
