"""MAID Subgame Perfect Equilibrium analysis - standalone for plugin service."""

from __future__ import annotations

from typing import Any

from pycid_plugin.pycid_utils import maid_game_to_pycid, format_ne_result


def run_maid_spe(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compute Subgame Perfect Equilibria for a MAID.

    Subgame Perfect Equilibrium (SPE) is a refinement of Nash equilibrium
    that requires the strategy profile to be a Nash equilibrium in every
    subgame of the original game.

    Args:
        game: Deserialized MAIDGame dict.
        config: Optional config with 'solver' key.
            solver: "enumpure" for pure SPE (default).

    Returns:
        Dict with 'summary' and 'details' keys.
    """
    config = config or {}
    solver_type = config.get("solver", "enumpure")

    try:
        macid = maid_game_to_pycid(game)

        # Use get_all_pure_spe which is available in the current PyCID version
        spe_list = macid.get_all_pure_spe()

        equilibria = format_ne_result(spe_list, game)

        solver_used = solver_type
        count = len(equilibria)
        exhaustive = True  # Pure enumeration is exhaustive

        if count == 0:
            summary = "No subgame perfect equilibria found"
        elif count == 1:
            summary = "1 subgame perfect equilibrium"
        else:
            summary = f"{count} subgame perfect equilibria"

        return {
            "summary": summary,
            "details": {
                "equilibria": equilibria,
                "solver": solver_used,
                "exhaustive": exhaustive,
            },
        }

    except Exception as e:
        return {
            "summary": f"Error: {str(e)}",
            "details": {"error": str(e), "equilibria": []},
        }
