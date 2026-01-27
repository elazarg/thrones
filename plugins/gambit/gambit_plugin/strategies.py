"""Strategy enumeration and payoff resolution utilities.

Duplicated from app/core/strategies.py for plugin isolation.
These functions operate on plain dicts (deserialized game JSON),
not Pydantic models, since the plugin doesn't import app.models.
"""
from __future__ import annotations

from itertools import product
from typing import Any, Mapping


def enumerate_strategies(game: dict[str, Any]) -> dict[str, list[Mapping[str, str]]]:
    """Enumerate all pure strategies for each player.

    Args:
        game: Deserialized game dict with 'players', 'nodes' keys.

    Returns:
        Dict mapping player name to list of strategies.
        Each strategy maps node_id -> action_label.
    """
    players = game["players"]
    nodes = game["nodes"]
    strategies: dict[str, list[Mapping[str, str]]] = {}

    for player in players:
        player_nodes = [
            (nid, node) for nid, node in nodes.items() if node["player"] == player
        ]
        if not player_nodes:
            strategies[player] = [{}]
            continue

        # Group nodes by information set
        info_sets: dict[str, list[tuple[str, dict]]] = {}
        for nid, node in player_nodes:
            key = node.get("information_set") or f"_singleton_{nid}"
            info_sets.setdefault(key, []).append((nid, node))

        info_set_keys = list(info_sets.keys())
        action_sets = []
        for key in info_set_keys:
            nodes_in_set = info_sets[key]
            action_sets.append([a["label"] for a in nodes_in_set[0][1]["actions"]])

        player_strategies: list[Mapping[str, str]] = []
        for action_combo in product(*action_sets):
            strategy: dict[str, str] = {}
            for key, action in zip(info_set_keys, action_combo, strict=True):
                for nid, _ in info_sets[key]:
                    strategy[nid] = action
            player_strategies.append(strategy)

        strategies[player] = player_strategies

    return strategies


def resolve_payoffs(
    game: dict[str, Any], profile: Mapping[str, Mapping[str, str]]
) -> dict[str, float]:
    """Simulate a strategy profile to get terminal payoffs.

    Args:
        game: Deserialized game dict with 'root', 'nodes', 'outcomes'.
        profile: Maps player name -> (node_id -> action_label).

    Returns:
        Dict mapping player name to payoff.
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

        player_strategy = profile.get(node["player"])
        if player_strategy is None:
            raise ValueError(f"Profile is missing strategy for player '{node['player']}'")

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
