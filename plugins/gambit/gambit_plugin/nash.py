"""Nash equilibrium analysis - standalone for plugin service."""

from __future__ import annotations

from typing import Any

import pygambit as gbt

from gambit_plugin.gambit_utils import extensive_to_gambit_table, normal_form_to_gambit
from gambit_plugin.strategies import enumerate_strategies, resolve_payoffs


def run_nash(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compute Nash equilibria for a game.

    Args:
        game: Deserialized game dict (extensive or normal form).
        config: Optional config with 'solver', 'max_equilibria' keys.

    Returns:
        Dict with 'summary' and 'details' keys.
    """
    config = config or {}
    solver_type = config.get("solver", "exhaustive")
    max_equilibria = config.get("max_equilibria")
    format_name = game.get("format_name", "extensive")

    # Convert to Gambit game
    if format_name == "normal":
        gambit_game = normal_form_to_gambit(game)
    else:
        strategies = enumerate_strategies(game)
        gambit_game = extensive_to_gambit_table(game, strategies, resolve_payoffs)

    # Select solver
    if solver_type == "quick":
        result = None
        solver_name = "gambit-logit"
        stop_after = max_equilibria if max_equilibria else 1

        try:
            result = gbt.nash.logit_solve(gambit_game)
        except (ValueError, IndexError, RuntimeError):
            pass

        if result is None or (stop_after > 1 and len(result.equilibria) < stop_after):
            try:
                result = gbt.nash.lcp_solve(
                    gambit_game, stop_after=stop_after, rational=False
                )
                solver_name = "gambit-lcp"
            except (ValueError, IndexError, RuntimeError):
                pass

        if result is None:
            try:
                result = gbt.nash.enummixed_solve(gambit_game, rational=False)
                solver_name = "gambit-enummixed"
            except (ValueError, IndexError, RuntimeError) as e:
                return {
                    "summary": f"All Nash solvers failed: {e}",
                    "details": {
                        "equilibria": [],
                        "solver": "none",
                        "exhaustive": False,
                        "error": str(e),
                    },
                }

        exhaustive = len(result.equilibria) < stop_after

    elif solver_type == "pure":
        try:
            result = gbt.nash.enumpure_solve(gambit_game)
        except (ValueError, IndexError, RuntimeError) as e:
            return {
                "summary": f"Pure strategy solver failed: {e}",
                "details": {
                    "equilibria": [],
                    "solver": "gambit-enumpure",
                    "exhaustive": False,
                    "error": str(e),
                },
            }
        solver_name = "gambit-enumpure"
        exhaustive = True

    elif solver_type == "approximate":
        result = None
        solver_name = "gambit-simpdiv"
        try:
            start = gambit_game.mixed_strategy_profile(rational=True)
            result = gbt.nash.simpdiv_solve(start)
        except (ValueError, IndexError, RuntimeError) as e:
            # Simpdiv can fail on certain game structures
            try:
                result = gbt.nash.logit_solve(gambit_game)
                solver_name = "gambit-logit"
            except (ValueError, IndexError, RuntimeError):
                pass

        if result is None:
            return {
                "summary": "No approximate equilibrium found (game may be too large or have unsupported structure)",
                "details": {"equilibria": [], "solver": "none", "exhaustive": False},
            }
        exhaustive = False

    elif solver_type == "logit":
        try:
            result = gbt.nash.logit_solve(gambit_game)
        except (ValueError, IndexError, RuntimeError) as e:
            return {
                "summary": f"Logit solver failed: {e}",
                "details": {
                    "equilibria": [],
                    "solver": "gambit-logit",
                    "exhaustive": False,
                    "error": str(e),
                },
            }
        solver_name = "gambit-logit"
        exhaustive = False

    elif solver_type == "lp":
        # Linear programming solver - only works for 2-player constant-sum games
        try:
            result = gbt.nash.lp_solve(gambit_game)
        except (ValueError, IndexError, RuntimeError) as e:
            return {
                "summary": f"LP solver failed (requires 2-player constant-sum game): {e}",
                "details": {
                    "equilibria": [],
                    "solver": "gambit-lp",
                    "exhaustive": False,
                    "error": str(e),
                },
            }
        solver_name = "gambit-lp"
        exhaustive = True

    elif solver_type == "liap":
        # Lyapunov function minimization - finds approximate equilibria
        maxregret = config.get("maxregret", 1e-6)
        try:
            result = gbt.nash.liap_solve(gambit_game, maxregret=maxregret)
        except (ValueError, IndexError, RuntimeError) as e:
            return {
                "summary": f"Lyapunov solver failed: {e}",
                "details": {
                    "equilibria": [],
                    "solver": "gambit-liap",
                    "exhaustive": False,
                    "error": str(e),
                },
            }
        solver_name = "gambit-liap"
        exhaustive = False

    else:
        # Default: exhaustive
        try:
            result = gbt.nash.enummixed_solve(gambit_game, rational=False)
        except (ValueError, IndexError, RuntimeError) as e:
            return {
                "summary": f"Exhaustive solver failed: {e}",
                "details": {
                    "equilibria": [],
                    "solver": "gambit-enummixed",
                    "exhaustive": False,
                    "error": str(e),
                },
            }
        solver_name = "gambit-enummixed"
        exhaustive = True

    try:
        equilibria = [_to_equilibrium(gambit_game, eq) for eq in result.equilibria]
    except (IndexError, KeyError, RuntimeError) as e:
        # Conversion to our format failed - likely a pygambit internal issue
        return {
            "summary": f"Error processing equilibrium results: {e}",
            "details": {
                "equilibria": [],
                "solver": solver_name,
                "exhaustive": False,
                "error": str(e),
            },
        }

    count = len(equilibria)
    suffix = "" if exhaustive else "+"
    if count == 0:
        summary = "No Nash equilibria found"
    elif count == 1:
        summary = f"1 Nash equilibrium{suffix}"
    else:
        summary = f"{count} Nash equilibria{suffix}"

    return {
        "summary": summary,
        "details": {
            "equilibria": equilibria,
            "solver": solver_name,
            "exhaustive": exhaustive,
        },
    }


def _clean_float(value: float, tolerance: float = 1e-6) -> float:
    """Round floats and snap to common rational values."""
    if abs(value) < tolerance:
        return 0.0

    common_fractions = [
        0.0,
        1.0,
        0.5,
        1 / 3,
        2 / 3,
        0.25,
        0.75,
        0.2,
        0.4,
        0.6,
        0.8,
        1 / 6,
        5 / 6,
        1 / 8,
        3 / 8,
        5 / 8,
        7 / 8,
    ]
    for frac in common_fractions:
        if abs(value - frac) < tolerance:
            return frac

    nearest_int = round(value)
    if abs(value - nearest_int) < tolerance:
        return float(nearest_int)

    return round(value, 6)


def _to_equilibrium(game: gbt.Game, eq) -> dict[str, Any]:
    """Convert a Gambit equilibrium to a serializable dict."""
    strategies: dict[str, dict[str, float]] = {}
    for strategy, probability in eq:
        player_label = strategy.player.label
        strategies.setdefault(player_label, {})[strategy.label] = _clean_float(
            float(probability)
        )

    payoffs = {
        player.label: _clean_float(float(eq.payoff(player))) for player in game.players
    }

    pure = all(p in (0.0, 1.0) for probs in strategies.values() for p in probs.values())
    if pure:
        desc_parts = []
        for player, strats in strategies.items():
            chosen = max(strats, key=strats.get)
            desc_parts.append(f"{player} plays {chosen}")
        description = "Pure: " + ", ".join(desc_parts)
    else:
        description = "Mixed equilibrium"

    return {
        "description": description,
        "behavior_profile": strategies,
        "outcomes": payoffs,
        "strategies": strategies,
        "payoffs": payoffs,
    }
