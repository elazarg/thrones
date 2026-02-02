"""Backward Induction analysis - SPE for perfect-information games."""

from __future__ import annotations

import io
from typing import Any

import pygambit as gbt


def run_backward_induction(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compute Subgame Perfect Equilibrium via backward induction.

    Backward induction finds the SPE for perfect-information extensive-form
    games by solving from terminal nodes upward.

    Args:
        game: Deserialized game dict (extensive form with efg_content).
        config: Optional configuration (currently unused).

    Returns:
        Dict with 'summary' and 'details' keys.
    """
    format_name = game.get("format_name", "extensive")

    if format_name == "normal":
        return {
            "summary": "Backward induction requires extensive-form games",
            "details": {
                "error": "Cannot apply backward induction to normal-form games",
                "equilibria": [],
            },
        }

    # Check for EFG content
    efg_content = game.get("efg_content")
    if not efg_content:
        return {
            "summary": "No EFG content available",
            "details": {
                "error": "Backward induction requires original EFG content",
                "equilibria": [],
            },
        }

    try:
        # Load native Gambit game from EFG content
        gambit_game = gbt.read_efg(io.StringIO(efg_content))

        # Check for perfect information
        if not _is_perfect_information_gambit(gambit_game):
            return {
                "summary": "Game has imperfect information",
                "details": {
                    "error": "Backward induction requires perfect-information games. "
                    "Use Nash Equilibrium solvers for games with simultaneous moves or hidden information.",
                    "equilibria": [],
                },
            }

        # Run backward induction
        result = gbt.nash.backward_induction_solve(gambit_game)

        equilibria = [_to_equilibrium(gambit_game, eq) for eq in result.equilibria]

        count = len(equilibria)
        if count == 0:
            summary = "No SPE found"
        elif count == 1:
            summary = "1 Subgame Perfect Equilibrium"
        else:
            summary = f"{count} Subgame Perfect Equilibria"

        return {
            "summary": summary,
            "details": {
                "equilibria": equilibria,
                "solver": "backward-induction",
                "exhaustive": True,
            },
        }

    except (ValueError, RuntimeError) as e:
        return {
            "summary": f"Backward induction failed: {e}",
            "details": {
                "equilibria": [],
                "solver": "backward-induction",
                "error": str(e),
            },
        }


def _is_perfect_information_gambit(gambit_game: gbt.Game) -> bool:
    """Check if a Gambit game has perfect information.

    A game has perfect information if every information set contains
    exactly one decision node.
    """
    for player in gambit_game.players:
        for infoset in player.infosets:
            if len(infoset.members) > 1:
                return False
    return True


def _clean_float(value: float, tolerance: float = 1e-6) -> float:
    """Round floats and snap to common rational values."""
    if abs(value) < tolerance:
        return 0.0

    common_fractions = [0.0, 1.0, 0.5, 1 / 3, 2 / 3, 0.25, 0.75]
    for frac in common_fractions:
        if abs(value - frac) < tolerance:
            return frac

    nearest_int = round(value)
    if abs(value - nearest_int) < tolerance:
        return float(nearest_int)

    return round(value, 6)


def _to_equilibrium(game: gbt.Game, eq) -> dict[str, Any]:
    """Convert a Gambit behavior profile equilibrium to a serializable dict."""
    strategies: dict[str, dict[str, float]] = {}

    # For behavior strategies (extensive form), iterate over info sets
    for player in game.players:
        player_strategies: dict[str, float] = {}
        for infoset in player.infosets:
            for action in infoset.actions:
                prob = float(eq[action])
                if prob > 1e-6:
                    key = f"{infoset.label}:{action.label}" if infoset.label else action.label
                    player_strategies[key] = _clean_float(prob)
        strategies[player.label] = player_strategies

    # Compute payoffs
    payoffs = {}
    for player in game.players:
        payoffs[player.label] = _clean_float(float(eq.payoff(player)))

    # Build description
    desc_parts = []
    for player in game.players:
        chosen_actions = [
            action.label
            for infoset in player.infosets
            for action in infoset.actions
            if float(eq[action]) > 0.5
        ]
        if chosen_actions:
            desc_parts.append(f"{player.label} plays {'/'.join(chosen_actions)}")

    description = "SPE: " + ", ".join(desc_parts) if desc_parts else "Subgame Perfect Equilibrium"

    return {
        "description": description,
        "behavior_profile": strategies,
        "strategies": strategies,
        "payoffs": payoffs,
    }
