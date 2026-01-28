"""Strategy enumeration and payoff resolution for extensive-form games.

This module operates on plain dicts (JSON-like structures) rather than
Pydantic models, enabling use by both:
- The core app (via wrapper functions that convert models to dicts)
- Plugins (which receive deserialized JSON directly)

Game dict structure expected:
    {
        "players": ["Alice", "Bob"],
        "root": "n1",
        "nodes": {
            "n1": {
                "player": "Alice",
                "information_set": "h1",  # optional, None means singleton
                "actions": [
                    {"label": "Left", "target": "n2"},
                    {"label": "Right", "target": "o1"}
                ]
            },
            ...
        },
        "outcomes": {
            "o1": {"payoffs": {"Alice": 1.0, "Bob": 2.0}},
            ...
        }
    }
"""
from __future__ import annotations

from itertools import product
from typing import Any, Iterator, Mapping


def iter_strategies(
    game: dict[str, Any],
    player: str,
) -> Iterator[dict[str, str]]:
    """Lazily enumerate all pure strategies for a player.

    A strategy is a complete plan: one action for each information set.
    Nodes in the same information set must have the same action assigned,
    since the player cannot distinguish between them.

    This generator yields strategies one at a time, allowing early termination
    if not all strategies are needed (e.g., when searching for a dominating
    strategy).

    Args:
        game: Deserialized game dict with 'nodes' key.
        player: The player whose strategies to enumerate.

    Yields:
        Strategy dicts mapping node_id -> action_label.
    """
    nodes = game["nodes"]

    # Find all nodes belonging to this player
    player_nodes = [
        (nid, node) for nid, node in nodes.items() if node["player"] == player
    ]

    if not player_nodes:
        # Player has no decision nodes - single empty strategy
        yield {}
        return

    # Group nodes by information set
    # Nodes with None/missing info_set are treated as singletons
    info_sets: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for nid, node in player_nodes:
        key = node.get("information_set") or f"_singleton_{nid}"
        info_sets.setdefault(key, []).append((nid, node))

    # Get actions for each info set (use first node's actions - all should be same)
    info_set_keys = list(info_sets.keys())
    action_sets = []
    for key in info_set_keys:
        nodes_in_set = info_sets[key]
        actions = [a["label"] for a in nodes_in_set[0][1]["actions"]]
        action_sets.append(actions)

    # Enumerate: one action per info set, applied to all nodes in that set
    for action_combo in product(*action_sets):
        strategy: dict[str, str] = {}
        for key, action in zip(info_set_keys, action_combo, strict=True):
            for nid, _ in info_sets[key]:
                strategy[nid] = action
        yield strategy


def all_strategies(game: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    """Enumerate all pure strategies for each player.

    This is a convenience function that collects all strategies into lists.
    For memory efficiency when not all strategies are needed, use
    `iter_strategies()` instead.

    Args:
        game: Deserialized game dict with 'players', 'nodes' keys.

    Returns:
        Dict mapping player name to list of strategies.
        Each strategy maps node_id -> action_label.
    """
    players = game["players"]
    return {
        player: list(iter_strategies(game, player))
        for player in players
    }


def estimate_strategy_count(game: dict[str, Any]) -> int:
    """Estimate total strategy profile count WITHOUT enumerating.

    This is O(nodes) instead of O(product of all action counts), which
    could be exponential for games with many information sets.

    Args:
        game: Deserialized game dict with 'players', 'nodes' keys.

    Returns:
        Estimated total number of strategy profiles (capped at 10M).
    """
    players = game["players"]
    nodes = game["nodes"]
    player_strategy_counts: dict[str, int] = {}

    for player in players:
        player_nodes = [
            (nid, node) for nid, node in nodes.items() if node["player"] == player
        ]
        if not player_nodes:
            player_strategy_counts[player] = 1
            continue

        # Group nodes by information set
        info_sets: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for nid, node in player_nodes:
            key = node.get("information_set") or f"_singleton_{nid}"
            info_sets.setdefault(key, []).append((nid, node))

        # Count = product of action counts for each info set
        count = 1
        for nodes_in_set in info_sets.values():
            num_actions = len(nodes_in_set[0][1]["actions"])
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
    game: dict[str, Any],
    profile: Mapping[str, Mapping[str, str]],
) -> dict[str, float]:
    """Simulate a strategy profile to get terminal payoffs for all players.

    Traverses the game tree following the actions specified in the profile
    until reaching a terminal outcome.

    Args:
        game: Deserialized game dict with 'root', 'nodes', 'outcomes'.
        profile: Maps player name -> (node_id -> action_label).

    Returns:
        Dict mapping player name to payoff.

    Raises:
        ValueError: If profile is missing a player or action, or if no
            terminal outcome is reached.
    """
    nodes = game["nodes"]
    outcomes = game["outcomes"]
    current = game["root"]
    visited: set[str] = set()

    while current and current not in visited:
        visited.add(current)
        node = nodes.get(current)
        if not node:
            break

        player = node["player"]
        player_strategy = profile.get(player)
        if player_strategy is None:
            raise ValueError(f"Profile is missing strategy for player '{player}'")

        if current not in player_strategy:
            raise ValueError(f"Profile is missing action for node '{current}'")

        action_label = player_strategy[current]
        action = next((a for a in node["actions"] if a["label"] == action_label), None)
        if action is None or action.get("target") is None:
            break

        target = action["target"]
        if target in outcomes:
            return outcomes[target]["payoffs"]
        current = target

    raise ValueError("Failed to reach a terminal outcome when simulating strategies")


def resolve_payoff(
    game: dict[str, Any],
    player: str,
    profile: Mapping[str, Mapping[str, str]],
) -> float:
    """Resolve the payoff for a single player given a strategy profile.

    Convenience wrapper around resolve_payoffs for when only one player's
    payoff is needed (e.g., dominance checking).

    Args:
        game: Deserialized game dict.
        player: The player whose payoff to return.
        profile: Maps player name -> (node_id -> action_label).

    Returns:
        The payoff for the specified player.

    Raises:
        ValueError: If profile is invalid or no terminal outcome reached.
    """
    payoffs = resolve_payoffs(game, profile)
    return payoffs.get(player, 0.0)
