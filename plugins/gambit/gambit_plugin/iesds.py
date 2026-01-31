"""IESDS analysis - Iterated Elimination of Strictly Dominated Strategies."""

from __future__ import annotations

from typing import Any

import pygambit as gbt

from gambit_plugin.gambit_utils import extensive_to_gambit_table, normal_form_to_gambit
from gambit_plugin.strategies import enumerate_strategies, resolve_payoffs


def run_iesds(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Run IESDS on a game.

    Args:
        game: Deserialized game dict (extensive or normal form).
        config: Optional configuration (currently unused).

    Returns:
        Dict with 'summary' and 'details' keys.
    """
    format_name = game.get("format_name", "extensive")

    if format_name == "normal":
        gambit_game = normal_form_to_gambit(game)
    else:
        strategies = enumerate_strategies(game)
        gambit_game = extensive_to_gambit_table(game, strategies, resolve_payoffs)

    support = gambit_game.strategy_support_profile()
    eliminated: list[dict[str, str | int]] = []
    rounds = 0

    while True:
        rounds += 1
        new_support = gbt.supports.undominated_strategies_solve(support, strict=True)

        eliminated_this_round = []
        for player in gambit_game.players:
            for strategy in player.strategies:
                if strategy in support and strategy not in new_support:
                    eliminated_this_round.append(
                        {
                            "player": player.label,
                            "strategy": strategy.label,
                            "round": rounds,
                        }
                    )

        if not eliminated_this_round:
            break

        eliminated.extend(eliminated_this_round)
        support = new_support

        if rounds > 100:
            break

    surviving: dict[str, list[str]] = {}
    for player in gambit_game.players:
        surviving[player.label] = [s.label for s in player.strategies if s in support]

    summary = _summarize(eliminated, rounds, surviving)
    return {
        "summary": summary,
        "details": {
            "eliminated": eliminated,
            "rounds": rounds - 1 if rounds > 0 else 0,
            "surviving": surviving,
        },
    }


def _summarize(
    eliminated: list[dict],
    rounds: int,
    surviving: dict[str, list[str]],
) -> str:
    if not eliminated:
        return "No dominated strategies found"
    count = len(eliminated)
    rounds_actual = rounds - 1 if rounds > 1 else rounds
    if count == 1:
        e = eliminated[0]
        return f"Eliminated: {e['player']}.{e['strategy']}"
    return f"{count} strategies eliminated in {rounds_actual} round{'s' if rounds_actual != 1 else ''}"
