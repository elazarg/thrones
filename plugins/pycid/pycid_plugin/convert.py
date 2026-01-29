"""MAID to EFG conversion.

Converts Multi-Agent Influence Diagrams to Extensive Form Games.
Since MAIDs are Bayesian networks (not game trees), this conversion
creates a sequential representation where players move in order,
with information sets encoding simultaneity.
"""
from __future__ import annotations

import uuid
from typing import Any

from pycid_plugin.pycid_utils import maid_game_to_pycid


def convert_maid_to_efg(game: dict[str, Any]) -> dict[str, Any]:
    """Convert a MAID game dict to ExtensiveFormGame dict.

    For simultaneous games, creates a sequential tree where the second
    player's nodes are in a single information set (encoding that they
    don't observe the first player's move).

    Args:
        game: Deserialized MAIDGame dict.

    Returns:
        Dict matching ExtensiveFormGame schema.

    Raises:
        ValueError: If conversion fails.
    """
    try:
        macid = maid_game_to_pycid(game)
        return _macid_to_efg_dict(macid, game)
    except Exception as e:
        raise ValueError(f"MAID to EFG conversion failed: {e}") from e


def _macid_to_efg_dict(macid, game: dict[str, Any]) -> dict[str, Any]:
    """Convert a PyCID MACID to ExtensiveFormGame dict.

    Args:
        macid: PyCID MACID object.
        game: Original MAID game dict for reference.

    Returns:
        Dict matching ExtensiveFormGame schema.
    """
    # Get agents and their decision nodes
    agents = list(macid.agents)
    if len(agents) < 1:
        raise ValueError("MAID must have at least one agent")

    # Build mapping from agent to decision nodes and their domains
    agent_decisions: dict[str, list[str]] = {}
    decision_domains: dict[str, list[str]] = {}

    for agent in agents:
        agent_decisions[agent] = list(macid.agent_decisions.get(agent, []))

    # Get domains from the game dict - keep both original and string versions
    # String domains are used for tree labels, original domains for PyCID calls
    original_domains: dict[str, list] = {}
    for node in game.get("nodes", []):
        if node.get("type") == "decision" and node.get("domain"):
            original_domains[node["id"]] = node["domain"]
            decision_domains[node["id"]] = [str(d) for d in node["domain"]]

    # For simple 2-player simultaneous games, create sequential tree
    # with information sets encoding simultaneity
    nodes: dict[str, dict[str, Any]] = {}
    outcomes: dict[str, dict[str, Any]] = {}

    # Calculate all strategy profiles and their payoffs
    all_decision_nodes = []
    all_domains = []
    all_original_domains = []
    for agent in agents:
        for dec in agent_decisions.get(agent, []):
            all_decision_nodes.append((agent, dec))
            domain = decision_domains.get(dec, ["0", "1"])
            all_domains.append(domain)
            all_original_domains.append(original_domains.get(dec, [0, 1]))

    # Build the tree
    counter = [0]

    def build_subtree(
        decision_idx: int,
        strategy_prefix: tuple[str, ...],
        info_set_base: dict[str, int],
    ) -> str:
        """Build subtree recursively."""
        if decision_idx >= len(all_decision_nodes):
            # Terminal node - compute payoff
            return create_outcome(strategy_prefix)

        agent, dec_node = all_decision_nodes[decision_idx]
        domain = all_domains[decision_idx]

        node_id = f"n_{counter[0]}"
        counter[0] += 1

        # Determine information set
        # For simultaneous games, all nodes for an agent at the same
        # decision point share an information set
        info_set_id = f"h_{agent}_{info_set_base.get(agent, 0)}"

        actions = []
        for action in domain:
            new_prefix = strategy_prefix + (action,)
            new_info_base = info_set_base.copy()
            new_info_base[agent] = new_info_base.get(agent, 0) + 1
            target = build_subtree(decision_idx + 1, new_prefix, new_info_base)
            actions.append({"label": action, "target": target})

        nodes[node_id] = {
            "id": node_id,
            "player": agent,
            "actions": actions,
            "information_set": info_set_id,
        }

        return node_id

    def create_outcome(strategy: tuple[str, ...]) -> str:
        """Create outcome for a strategy profile."""
        outcome_id = f"o_{counter[0]}"
        counter[0] += 1

        # Compute expected utilities for this strategy profile
        payoffs = compute_payoffs(
            macid, game, agents, all_decision_nodes, strategy, all_original_domains
        )

        # Create label from strategy
        parts = []
        for i, (agent, dec) in enumerate(all_decision_nodes):
            parts.append(f"{dec}={strategy[i]}")
        label = ", ".join(parts)

        outcomes[outcome_id] = {
            "label": label,
            "payoffs": payoffs,
        }
        return outcome_id

    if not all_decision_nodes:
        raise ValueError("MAID has no decision nodes")

    root_id = build_subtree(0, (), {})

    return {
        "format_name": "extensive",
        "id": str(uuid.uuid4()),
        "title": game.get("title", "Converted MAID"),
        "players": agents,
        "root": root_id,
        "nodes": nodes,
        "outcomes": outcomes,
        "tags": ["converted", "maid-to-efg"],
    }


def compute_payoffs(
    macid,
    game: dict[str, Any],
    agents: list[str],
    decisions: list[tuple[str, str]],
    strategy: tuple[str, ...],
    original_domains: list[list] | None = None,
) -> dict[str, float]:
    """Compute expected payoffs for a strategy profile.

    Args:
        macid: PyCID MACID object.
        game: Original MAID game dict.
        agents: List of agent names.
        decisions: List of (agent, decision_node) tuples.
        strategy: Strategy profile as tuple of actions (as strings).
        original_domains: Original domain values for each decision (to map strings back).

    Returns:
        Dict mapping agent name to payoff.
    """
    # Build intervention dict, converting string strategies back to original domain values
    intervention = {}
    for i, (agent, dec_node) in enumerate(decisions):
        action_str = strategy[i]
        # Convert string action back to original domain value type
        if original_domains and i < len(original_domains):
            orig_domain = original_domains[i]
            # Find matching value in original domain
            for orig_val in orig_domain:
                if str(orig_val) == action_str:
                    intervention[dec_node] = orig_val
                    break
            else:
                # Fallback: try to convert to int if it looks numeric
                if action_str.lstrip("-").isdigit():
                    intervention[dec_node] = int(action_str)
                else:
                    intervention[dec_node] = action_str
        else:
            intervention[dec_node] = action_str

    # Compute expected utility for each agent
    payoffs = {}
    for agent in agents:
        try:
            eu = macid.expected_utility(intervention, agent=agent)
            payoffs[agent] = float(eu)
        except (RuntimeError, ValueError):
            # Fall back to computing from CPDs if expected_utility fails
            # (e.g., when policies are required but not imputed)
            payoffs[agent] = _compute_utility_from_cpds(game, agent, strategy, decisions)

    return payoffs


def _compute_utility_from_cpds(
    game: dict[str, Any],
    agent: str,
    strategy: tuple[str, ...],
    decisions: list[tuple[str, str]],
) -> float:
    """Compute utility from CPD tables when MACID computation fails.

    Args:
        game: MAID game dict.
        agent: Agent to compute utility for.
        strategy: Strategy profile.
        decisions: List of (agent, decision_node) tuples.

    Returns:
        Expected utility value.
    """
    # Find utility nodes for this agent
    utility_nodes = []
    for node in game.get("nodes", []):
        if node.get("type") == "utility" and node.get("agent") == agent:
            utility_nodes.append(node)

    if not utility_nodes:
        return 0.0

    total_utility = 0.0

    for util_node in utility_nodes:
        # Find the CPD for this utility node
        cpd = None
        for c in game.get("cpds", []):
            if c["node"] == util_node["id"]:
                cpd = c
                break

        if cpd is None:
            continue

        # Get the domain of the utility node
        domain = util_node.get("domain", [0])

        # Map decision actions to indices
        dec_map = {}
        for i, (_, dec_node) in enumerate(decisions):
            # Find the decision node's domain
            for node in game.get("nodes", []):
                if node["id"] == dec_node:
                    dec_domain = node.get("domain", ["0", "1"])
                    try:
                        dec_map[dec_node] = dec_domain.index(strategy[i])
                    except ValueError:
                        dec_map[dec_node] = int(strategy[i]) if strategy[i].isdigit() else 0
                    break

        # Compute the column index in the CPD table
        parents = cpd.get("parents", [])
        if not parents:
            # No parents - just take expected value
            values = cpd.get("values", [[]])
            if values and values[0]:
                probs = values[0]
                for i, p in enumerate(probs):
                    if i < len(domain):
                        total_utility += float(domain[i]) * p
            continue

        # Calculate column index from parent values
        col_idx = 0
        multiplier = 1
        for parent in reversed(parents):
            if parent in dec_map:
                # Find parent cardinality
                for node in game.get("nodes", []):
                    if node["id"] == parent:
                        parent_card = len(node.get("domain", ["0", "1"]))
                        col_idx += dec_map[parent] * multiplier
                        multiplier *= parent_card
                        break

        # Get probability distribution over utility values
        values = cpd.get("values", [])
        for row_idx, row in enumerate(values):
            if col_idx < len(row):
                prob = row[col_idx]
                if row_idx < len(domain):
                    total_utility += float(domain[row_idx]) * prob

    return total_utility
