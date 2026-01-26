"""PyCID conversion utilities.

This module provides utilities for converting between our MAIDGame model
and PyCID's MACID class for analysis.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.models import MAIDGame

if TYPE_CHECKING:
    from pycid import MACID


def maid_game_to_pycid(game: MAIDGame) -> "MACID":
    """Convert a MAIDGame to a PyCID MACID object.

    Args:
        game: The MAIDGame to convert.

    Returns:
        A PyCID MACID object configured with the game's structure and CPDs.
    """
    from pycid import MACID
    from pgmpy.factors.discrete import TabularCPD
    import numpy as np

    # Build edge list
    edges = [(e.source, e.target) for e in game.edges]

    # Build agent_decisions and agent_utilities mappings
    agent_decisions: dict[str, list[str]] = {}
    agent_utilities: dict[str, list[str]] = {}

    for node in game.nodes:
        if node.type == "decision" and node.agent:
            if node.agent not in agent_decisions:
                agent_decisions[node.agent] = []
            agent_decisions[node.agent].append(node.id)
        elif node.type == "utility" and node.agent:
            if node.agent not in agent_utilities:
                agent_utilities[node.agent] = []
            agent_utilities[node.agent].append(node.id)

    # Create the MACID
    macid = MACID(
        edges=edges,
        agent_decisions=agent_decisions,
        agent_utilities=agent_utilities,
    )

    # Build a map of node domains from the nodes
    node_domains: dict[str, list] = {}
    for node in game.nodes:
        if node.domain:
            node_domains[node.id] = node.domain

    # Add CPDs
    cpd_kwargs: dict = {}
    for cpd in game.cpds:
        node_id = cpd.node
        parents = cpd.parents
        values = cpd.values

        if not parents:
            # No parents - simple domain or marginal distribution
            if len(values) == 1 and all(isinstance(v, (int, float)) for v in values[0]):
                # This is a probability distribution
                cpd_kwargs[node_id] = TabularCPD(
                    node_id,
                    len(values[0]),
                    np.array(values).T,
                )
            else:
                # This is a domain specification (list of possible values)
                if node_id in node_domains:
                    cpd_kwargs[node_id] = node_domains[node_id]
                else:
                    # Infer domain from values
                    cpd_kwargs[node_id] = list(range(len(values[0])))
        else:
            # Has parents - build TabularCPD
            # Get parent cardinalities
            parent_cards = []
            for parent in parents:
                if parent in node_domains:
                    parent_cards.append(len(node_domains[parent]))
                else:
                    # Try to infer from CPD structure
                    parent_node = game.get_node(parent)
                    if parent_node and parent_node.domain:
                        parent_cards.append(len(parent_node.domain))
                    else:
                        # Default to 2 (binary)
                        parent_cards.append(2)

            # Convert values to numpy array
            values_array = np.array(values)
            cpd_kwargs[node_id] = TabularCPD(
                node_id,
                len(values),
                values_array,
                evidence=parents,
                evidence_card=parent_cards,
            )

    # Add decision domains for nodes without explicit CPDs
    for node in game.nodes:
        if node.id not in cpd_kwargs:
            if node.type == "decision" and node.domain:
                cpd_kwargs[node.id] = node.domain
            elif node.domain:
                cpd_kwargs[node.id] = node.domain

    if cpd_kwargs:
        macid.add_cpds(**cpd_kwargs)

    return macid


def format_ne_result(
    ne_list: list,
    game: MAIDGame,
) -> list[dict]:
    """Format Nash equilibrium results from PyCID for API response.

    Args:
        ne_list: List of Nash equilibria from MACID.get_ne()
        game: The original MAIDGame for context

    Returns:
        List of formatted equilibrium dictionaries
    """
    formatted = []

    for i, ne in enumerate(ne_list):
        # Each NE is a list of StochasticFunctionCPDs (one per decision)
        strategies: dict[str, dict[str, float]] = {}
        description_parts = []

        for cpd in ne:
            decision_node = cpd.variable
            node = game.get_node(decision_node)
            agent = node.agent if node else "Unknown"

            # Extract strategy probabilities from CPD
            probs = cpd.get_values()
            domain = list(cpd.domain) if hasattr(cpd, 'domain') else list(range(len(probs)))

            # Build strategy dict
            strategy_probs = {}
            for j, action in enumerate(domain):
                prob = float(probs[j][0]) if len(probs.shape) > 1 else float(probs[j])
                if prob > 1e-6:  # Only include non-zero probabilities
                    strategy_probs[str(action)] = round(prob, 6)

            strategies[decision_node] = strategy_probs

            # Build description
            if len(strategy_probs) == 1:
                action = list(strategy_probs.keys())[0]
                description_parts.append(f"{agent} plays {action}")
            else:
                description_parts.append(f"{agent} mixes")

        # Determine if pure or mixed
        is_pure = all(
            len(s) == 1 for s in strategies.values()
        )

        formatted.append({
            "description": ("Pure: " if is_pure else "Mixed: ") + ", ".join(description_parts),
            "strategies": strategies,
            "behavior_profile": strategies,  # Alias for compatibility
        })

    return formatted
