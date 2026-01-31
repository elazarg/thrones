"""PyCID conversion utilities.

Moved from app/core/pycid_utils.py for plugin isolation.
Operates on plain dicts (deserialized game JSON).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from pgmpy.factors.discrete import TabularCPD
from pycid import MACID


def maid_game_to_pycid(game: dict[str, Any]) -> Any:
    """Convert a MAID game dict to a PyCID MACID object.

    Args:
        game: Deserialized MAIDGame dict.

    Returns:
        A PyCID MACID object.
    """

    edges = [(e["source"], e["target"]) for e in game["edges"]]

    agent_decisions: dict[str, list[str]] = {}
    agent_utilities: dict[str, list[str]] = {}

    for node in game["nodes"]:
        if node["type"] == "decision" and node.get("agent"):
            agent_decisions.setdefault(node["agent"], []).append(node["id"])
        elif node["type"] == "utility" and node.get("agent"):
            agent_utilities.setdefault(node["agent"], []).append(node["id"])

    macid = MACID(
        edges=edges,
        agent_decisions=agent_decisions,
        agent_utilities=agent_utilities,
    )

    node_domains: dict[str, list] = {}
    for node in game["nodes"]:
        if node.get("domain"):
            node_domains[node["id"]] = node["domain"]

    cpd_kwargs: dict = {}
    for cpd in game.get("cpds", []):
        node_id = cpd["node"]
        parents = cpd.get("parents", [])
        values = cpd["values"]

        if not parents:
            if len(values) == 1 and all(isinstance(v, (int, float)) for v in values[0]):
                cpd_kwargs[node_id] = TabularCPD(
                    node_id,
                    len(values[0]),
                    np.array(values).T,
                )
            else:
                if node_id in node_domains:
                    cpd_kwargs[node_id] = node_domains[node_id]
                else:
                    cpd_kwargs[node_id] = list(range(len(values[0])))
        else:
            parent_cards = []
            for parent in parents:
                if parent in node_domains:
                    parent_cards.append(len(node_domains[parent]))
                else:
                    parent_node = _get_node(game, parent)
                    if parent_node and parent_node.get("domain"):
                        parent_cards.append(len(parent_node["domain"]))
                    else:
                        parent_cards.append(2)

            values_array = np.array(values)
            cpd_kwargs[node_id] = TabularCPD(
                node_id,
                len(values),
                values_array,
                evidence=parents,
                evidence_card=parent_cards,
            )

    for node in game["nodes"]:
        if node["id"] not in cpd_kwargs:
            if node["type"] == "decision" and node.get("domain"):
                cpd_kwargs[node["id"]] = node["domain"]
            elif node.get("domain"):
                cpd_kwargs[node["id"]] = node["domain"]

    if cpd_kwargs:
        macid.add_cpds(**cpd_kwargs)

    return macid


def _get_node(game: dict[str, Any], node_id: str) -> dict | None:
    """Find a node by ID in a game dict."""
    for node in game.get("nodes", []):
        if node["id"] == node_id:
            return node
    return None


def format_ne_result(ne_list: list, game: dict[str, Any]) -> list[dict]:
    """Format Nash equilibrium results from PyCID for API response.

    Args:
        ne_list: List of Nash equilibria from MACID.get_ne()
        game: The original MAID game dict.

    Returns:
        List of formatted equilibrium dictionaries.
    """
    formatted = []

    for ne in ne_list:
        strategies: dict[str, dict[str, float]] = {}
        description_parts = []

        for cpd in ne:
            decision_node = cpd.variable
            node = _get_node(game, decision_node)
            agent = node.get("agent", "Unknown") if node else "Unknown"

            probs = cpd.get_values()
            domain = (
                list(cpd.domain) if hasattr(cpd, "domain") else list(range(len(probs)))
            )

            strategy_probs = {}
            for j, action in enumerate(domain):
                prob = float(probs[j][0]) if len(probs.shape) > 1 else float(probs[j])
                if prob > 1e-6:
                    strategy_probs[str(action)] = round(prob, 6)

            strategies[decision_node] = strategy_probs

            if len(strategy_probs) == 1:
                action = list(strategy_probs.keys())[0]
                description_parts.append(f"{agent} plays {action}")
            else:
                description_parts.append(f"{agent} mixes")

        is_pure = all(len(s) == 1 for s in strategies.values())

        formatted.append(
            {
                "description": ("Pure: " if is_pure else "Mixed: ")
                + ", ".join(description_parts),
                "strategies": strategies,
                "behavior_profile": strategies,
            }
        )

    return formatted
