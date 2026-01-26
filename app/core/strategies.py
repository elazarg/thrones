"""Core strategy enumeration and payoff resolution utilities.

These functions are used by multiple plugins and the EFG↔NFG conversion module.
Centralizing them here avoids duplication and ensures consistent behavior.
"""
from __future__ import annotations

from collections.abc import Mapping
from itertools import product
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.extensive_form import DecisionNode, ExtensiveFormGame


def enumerate_strategies(game: ExtensiveFormGame) -> dict[str, list[Mapping[str, str]]]:
    """Enumerate all pure strategies for each player.

    A strategy is a complete plan: one action for each information set.
    Nodes in the same information set must have the same action assigned,
    since the player cannot distinguish between them.

    Args:
        game: The extensive-form game.

    Returns:
        Dict mapping player name to list of strategies.
        Each strategy maps node_id -> action_label.
    """
    strategies: dict[str, list[Mapping[str, str]]] = {}

    for player in game.players:
        player_nodes = [node for node in game.nodes.values() if node.player == player]
        if not player_nodes:
            strategies[player] = [{}]
            continue

        # Group nodes by information set
        # Nodes with None info_set are treated as singletons (player can distinguish)
        info_sets: dict[str, list["DecisionNode"]] = {}
        for node in player_nodes:
            key = node.information_set if node.information_set else f"_singleton_{node.id}"
            info_sets.setdefault(key, []).append(node)

        # Get actions for each info set (use first node's actions - all should be same)
        info_set_keys = list(info_sets.keys())
        action_sets = []
        for key in info_set_keys:
            nodes_in_set = info_sets[key]
            action_sets.append([action.label for action in nodes_in_set[0].actions])

        # Enumerate: one action per info set, applied to all nodes in that set
        player_strategies: list[Mapping[str, str]] = []
        for action_combo in product(*action_sets):
            strategy: dict[str, str] = {}
            for key, action in zip(info_set_keys, action_combo, strict=True):
                for node in info_sets[key]:
                    strategy[node.id] = action
            player_strategies.append(strategy)

        strategies[player] = player_strategies

    return strategies


def estimate_strategy_count(game: ExtensiveFormGame) -> int:
    """Estimate total strategy profile count WITHOUT enumerating.

    This is O(nodes) instead of O(product of all action counts), which
    could be exponential for games with many information sets.

    Args:
        game: The extensive-form game.

    Returns:
        Estimated total number of strategy profiles (may be capped at 10M).
    """
    player_strategy_counts: dict[str, int] = {}

    for player in game.players:
        player_nodes = [node for node in game.nodes.values() if node.player == player]
        if not player_nodes:
            player_strategy_counts[player] = 1
            continue

        # Group nodes by information set
        info_sets: dict[str, list] = {}
        for node in player_nodes:
            key = node.information_set if node.information_set else f"_singleton_{node.id}"
            info_sets.setdefault(key, []).append(node)

        # Count = product of action counts for each info set
        count = 1
        for nodes_in_set in info_sets.values():
            num_actions = len(nodes_in_set[0].actions)
            count *= num_actions
            if count > 10_000_000:
                break
        player_strategy_counts[player] = count

    # Total profiles = product of each player's strategy count
    total = 1
    for count in player_strategy_counts.values():
        total *= count
        if total > 10_000_000:
            return total
    return total


def resolve_payoffs(
    game: ExtensiveFormGame, profile: Mapping[str, Mapping[str, str]]
) -> dict[str, float]:
    """Simulate a strategy profile to get terminal payoffs for all players.

    Traverses the game tree following the actions specified in the profile
    until reaching a terminal outcome.

    Args:
        game: The extensive-form game.
        profile: Maps player name -> (node_id -> action_label).

    Returns:
        Dict mapping player name to payoff.

    Raises:
        ValueError: If profile is missing a player or action, or if no
            terminal outcome is reached.
    """
    current = game.root
    visited: set[str] = set()

    while current and current not in visited:
        visited.add(current)
        node = game.nodes.get(current)
        if not node:
            break

        player_strategy = profile.get(node.player)
        if player_strategy is None:
            msg = f"Profile is missing strategy for player '{node.player}'"
            raise ValueError(msg)

        if node.id not in player_strategy:
            msg = f"Profile is missing action for node '{node.id}'"
            raise ValueError(msg)

        action_label = player_strategy[node.id]
        action = next((a for a in node.actions if a.label == action_label), None)
        if action is None or action.target is None:
            break
        if action.target in game.outcomes:
            return game.outcomes[action.target].payoffs
        current = action.target

    raise ValueError("Failed to reach a terminal outcome when simulating strategies")


def resolve_payoff(
    game: ExtensiveFormGame, player: str, profile: Mapping[str, Mapping[str, str]]
) -> float:
    """Resolve the payoff for a single player given a strategy profile.

    Convenience wrapper around resolve_payoffs for when only one player's
    payoff is needed (e.g., dominance checking).

    Args:
        game: The extensive-form game.
        player: The player whose payoff to return.
        profile: Maps player name -> (node_id -> action_label).

    Returns:
        The payoff for the specified player.

    Raises:
        ValueError: If profile is invalid or no terminal outcome reached.
    """
    payoffs = resolve_payoffs(game, profile)
    return payoffs.get(player, 0.0)
