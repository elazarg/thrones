"""Utilities for converting games to Gambit format.

Moved from app/core/gambit_utils.py for plugin isolation.
Operates on plain dicts (deserialized game JSON).
"""
from __future__ import annotations

from itertools import product
from typing import Any, Mapping

import pygambit as gbt


def normal_form_to_gambit(game: dict[str, Any]) -> gbt.Game:
    """Convert a normal-form game dict to a Gambit strategic form game."""
    strategies = game["strategies"]
    num_rows = len(strategies[0])
    num_cols = len(strategies[1])

    gambit_game = gbt.Game.new_table([num_rows, num_cols])
    gambit_game.title = game["title"]

    for player_index, player_name in enumerate(game["players"]):
        player = gambit_game.players[player_index]
        player.label = player_name
        for strat_index, strat_name in enumerate(strategies[player_index]):
            player.strategies[strat_index].label = strat_name

    for row in range(num_rows):
        for col in range(num_cols):
            outcome = gambit_game[row, col]
            payoffs = game["payoffs"][row][col]
            outcome[gambit_game.players[0]] = payoffs[0]
            outcome[gambit_game.players[1]] = payoffs[1]

    return gambit_game


def extensive_to_gambit_table(
    game: dict[str, Any],
    strategies: dict[str, list[Mapping[str, str]]],
    resolve_payoffs_fn: callable,
) -> gbt.Game:
    """Convert an extensive form game dict to a Gambit strategic form table."""
    players = game["players"]
    gambit_game = gbt.Game.new_table([len(strats) for strats in strategies.values()])
    gambit_game.title = game["title"]

    for player_index, player_name in enumerate(players):
        player = gambit_game.players[player_index]
        player.label = player_name
        for strat_index, strategy in enumerate(strategies[player_name]):
            labels = [strategy[node_id] for node_id in sorted(strategy.keys())]
            player.strategies[strat_index].label = "/".join(labels) if labels else "No moves"

    for profile_indices in product(*[range(len(strategies[player])) for player in players]):
        profile = {
            player: strategies[player][idx]
            for player, idx in zip(players, profile_indices, strict=True)
        }
        payoffs = resolve_payoffs_fn(game, profile)
        outcome = gambit_game[profile_indices]
        for p_index, player_name in enumerate(players):
            outcome[gambit_game.players[p_index]] = payoffs.get(player_name, 0.0)

    return gambit_game
