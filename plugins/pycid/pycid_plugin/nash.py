"""MAID Nash equilibrium analysis - standalone for plugin service."""
from __future__ import annotations

from typing import Any

from pycid_plugin.pycid_utils import maid_game_to_pycid, format_ne_result


def run_maid_nash(game: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compute Nash equilibria for a MAID.

    Args:
        game: Deserialized MAIDGame dict.
        config: Optional config with 'solver' key.

    Returns:
        Dict with 'summary' and 'details' keys.
    """
    config = config or {}
    solver_type = config.get("solver", "auto")

    try:
        macid = maid_game_to_pycid(game)

        solver_arg = None if solver_type == "auto" else solver_type
        ne_list = macid.get_ne(solver=solver_arg)

        equilibria = format_ne_result(ne_list, game)

        solver_used = solver_type if solver_type != "auto" else "auto"
        count = len(equilibria)
        exhaustive = solver_type in ("enummixed", "enumpure")
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
                "solver": solver_used,
                "exhaustive": exhaustive,
            },
        }

    except Exception as e:
        return {
            "summary": f"Error: {str(e)}",
            "details": {"error": str(e), "equilibria": []},
        }
