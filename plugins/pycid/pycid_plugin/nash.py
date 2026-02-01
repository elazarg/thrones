"""MAID Nash equilibrium analysis - standalone for plugin service."""

from __future__ import annotations

from typing import Any

from pycid_plugin.pycid_utils import maid_game_to_pycid, format_ne_result


def run_maid_nash(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compute pure-strategy Nash equilibria for a MAID.

    Note: PyCID only supports pure-strategy NE enumeration.
    For mixed equilibria, convert to extensive form and use Gambit.

    Args:
        game: Deserialized MAIDGame dict.
        config: Optional config (currently unused).

    Returns:
        Dict with 'summary' and 'details' keys.
    """
    try:
        macid = maid_game_to_pycid(game)

        # get_ne(solver='enumpure') returns list of pure Nash equilibria
        ne_list = macid.get_ne(solver='enumpure')

        equilibria = format_ne_result(ne_list, game)

        count = len(equilibria)
        if count == 0:
            summary = "No pure Nash equilibria found"
        elif count == 1:
            summary = "1 pure Nash equilibrium"
        else:
            summary = f"{count} pure Nash equilibria"

        return {
            "summary": summary,
            "details": {
                "equilibria": equilibria,
                "solver": "pycid-enumpure",
                "exhaustive": True,
            },
        }

    except Exception as e:
        return {
            "summary": f"Error: {str(e)}",
            "details": {"error": str(e), "equilibria": []},
        }
