"""Utilities for converting games to Gambit format.

Gambit is a library for game theory computations. These utilities convert
our internal game representations to Gambit's format for solving.

NOTE: This module assumes pygambit is available. It should only be imported
from code paths that have already verified PYGAMBIT_AVAILABLE is True.
"""
from __future__ import annotations

from collections.abc import Mapping
from itertools import product
from typing import TYPE_CHECKING

import pygambit as gbt

if TYPE_CHECKING:
    from app.models.extensive_form import ExtensiveFormGame
    from app.models.normal_form import NormalFormGame


def normal_form_to_gambit(game: "NormalFormGame") -> gbt.Game:
    """Convert a NormalFormGame to a Gambit strategic form game.

    Args:
        game: The normal form game with 2 players.

    Returns:
        A Gambit Game object ready for equilibrium computation.
    """
    num_rows = len(game.strategies[0])
    num_cols = len(game.strategies[1])

    gambit_game = gbt.Game.new_table([num_rows, num_cols])
    gambit_game.title = game.title

    # Set player labels and strategy labels
    for player_index, player_name in enumerate(game.players):
        player = gambit_game.players[player_index]
        player.label = player_name
        for strat_index, strat_name in enumerate(game.strategies[player_index]):
            player.strategies[strat_index].label = strat_name

    # Set payoffs
    for row in range(num_rows):
        for col in range(num_cols):
            outcome = gambit_game[row, col]
            payoffs = game.payoffs[row][col]
            outcome[gambit_game.players[0]] = payoffs[0]
            outcome[gambit_game.players[1]] = payoffs[1]

    return gambit_game


def extensive_to_gambit_table(
    game: ExtensiveFormGame,
    strategies: dict[str, list[Mapping[str, str]]],
    resolve_payoffs_fn: callable,
) -> gbt.Game:
    """Convert an extensive form game to a Gambit strategic form table.

    This builds a strategic form representation by enumerating all strategy
    profiles and computing their payoffs.

    Args:
        game: The extensive form game.
        strategies: Pre-enumerated strategies from enumerate_strategies().
        resolve_payoffs_fn: Function to resolve payoffs for a profile.
            Should have signature (game, profile) -> dict[str, float].

    Returns:
        A Gambit Game object in strategic form.
    """
    gambit_game = gbt.Game.new_table([len(strats) for strats in strategies.values()])
    gambit_game.title = game.title

    # Set player and strategy labels
    for player_index, player_name in enumerate(game.players):
        player = gambit_game.players[player_index]
        player.label = player_name
        for strat_index, strategy in enumerate(strategies[player_name]):
            labels = [strategy[node_id] for node_id in sorted(strategy.keys())]
            player.strategies[strat_index].label = "/".join(labels) if labels else "No moves"

    # Fill in payoffs for each strategy profile
    for profile_indices in product(*[range(len(strategies[player])) for player in game.players]):
        profile = {
            player: strategies[player][idx]
            for player, idx in zip(game.players, profile_indices, strict=True)
        }
        payoffs = resolve_payoffs_fn(game, profile)
        outcome = gambit_game[profile_indices]
        for p_index, player_name in enumerate(game.players):
            outcome[gambit_game.players[p_index]] = payoffs.get(player_name, 0.0)

    return gambit_game
