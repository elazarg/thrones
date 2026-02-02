"""CID-specific analyses: Value of Information, Value of Control, Decision Relevance."""

from __future__ import annotations

from typing import Any

from pycid_plugin.pycid_utils import _get_node, maid_game_to_pycid


def run_value_of_information(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compute Value of Information for a decision-observation pair.

    The Value of Information measures how much a decision-maker would
    benefit from observing a variable before making a decision.

    Args:
        game: Deserialized MAIDGame dict.
        config: Required config with:
            - decision: The decision node ID
            - observation: The observation node ID to evaluate
            - agent: (optional) The agent making the decision

    Returns:
        Dict with 'summary' and 'details' keys.
    """
    config = config or {}
    decision = config.get("decision")
    observation = config.get("observation")

    if not decision:
        return {
            "summary": "Error: 'decision' config parameter required",
            "details": {"error": "Must specify the decision node ID"},
        }

    if not observation:
        return {
            "summary": "Error: 'observation' config parameter required",
            "details": {"error": "Must specify the observation node ID to evaluate"},
        }

    try:
        macid = maid_game_to_pycid(game)

        # Compute value of information
        voi = macid.value_of_information(decision, observation)

        decision_node = _get_node(game, decision)
        obs_node = _get_node(game, observation)
        decision_label = decision_node.get("label", decision) if decision_node else decision
        obs_label = obs_node.get("label", observation) if obs_node else observation

        if voi > 0:
            summary = f"VOI({obs_label} -> {decision_label}) = {voi:.4f}"
        else:
            summary = f"No value from observing {obs_label} before {decision_label}"

        return {
            "summary": summary,
            "details": {
                "decision": decision,
                "observation": observation,
                "value_of_information": float(voi),
                "interpretation": "positive" if voi > 0 else "zero",
            },
        }

    except Exception as e:
        return {
            "summary": f"Error: {str(e)}",
            "details": {"error": str(e)},
        }


def run_value_of_control(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compute Value of Control for a decision-variable pair.

    The Value of Control measures how much a decision-maker would
    benefit from being able to control (set the value of) a variable.

    Args:
        game: Deserialized MAIDGame dict.
        config: Required config with:
            - decision: The decision node ID
            - variable: The variable node ID to evaluate control over

    Returns:
        Dict with 'summary' and 'details' keys.
    """
    config = config or {}
    decision = config.get("decision")
    variable = config.get("variable")

    if not decision:
        return {
            "summary": "Error: 'decision' config parameter required",
            "details": {"error": "Must specify the decision node ID"},
        }

    if not variable:
        return {
            "summary": "Error: 'variable' config parameter required",
            "details": {"error": "Must specify the variable node ID to evaluate"},
        }

    try:
        macid = maid_game_to_pycid(game)

        # Compute value of control
        voc = macid.value_of_control(decision, variable)

        decision_node = _get_node(game, decision)
        var_node = _get_node(game, variable)
        decision_label = decision_node.get("label", decision) if decision_node else decision
        var_label = var_node.get("label", variable) if var_node else variable

        if voc > 0:
            summary = f"VOC({var_label} @ {decision_label}) = {voc:.4f}"
        else:
            summary = f"No value from controlling {var_label} at {decision_label}"

        return {
            "summary": summary,
            "details": {
                "decision": decision,
                "variable": variable,
                "value_of_control": float(voc),
                "interpretation": "positive" if voc > 0 else "zero",
            },
        }

    except Exception as e:
        return {
            "summary": f"Error: {str(e)}",
            "details": {"error": str(e)},
        }


def run_decision_relevance(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Analyze which decisions are strategically relevant to each other.

    Uses r-reachability and s-reachability to determine which decisions
    can affect the outcomes of other decisions.

    Args:
        game: Deserialized MAIDGame dict.
        config: Optional config (currently unused).

    Returns:
        Dict with 'summary' and 'details' containing relevance matrix.
    """
    try:
        macid = maid_game_to_pycid(game)

        # Get all decision nodes
        decisions = []
        for node in game.get("nodes", []):
            if node.get("type") == "decision":
                decisions.append(node["id"])

        if not decisions:
            return {
                "summary": "No decision nodes found",
                "details": {"error": "MAID must have at least one decision node"},
            }

        # Build relevance matrix
        r_reachable: dict[str, list[str]] = {}
        s_reachable: dict[str, list[str]] = {}

        for d1 in decisions:
            r_reachable[d1] = []
            s_reachable[d1] = []
            for d2 in decisions:
                if d1 != d2:
                    try:
                        if macid.is_r_reachable(d1, d2):
                            r_reachable[d1].append(d2)
                    except Exception:
                        pass
                    try:
                        if macid.is_s_reachable(d1, d2):
                            s_reachable[d1].append(d2)
                    except Exception:
                        pass

        # Count relevant relationships
        r_count = sum(len(v) for v in r_reachable.values())
        s_count = sum(len(v) for v in s_reachable.values())

        if r_count == 0 and s_count == 0:
            summary = "No strategic dependencies between decisions"
        else:
            summary = f"{r_count} r-reachable, {s_count} s-reachable relationships"

        return {
            "summary": summary,
            "details": {
                "decisions": decisions,
                "r_reachable": r_reachable,
                "s_reachable": s_reachable,
                "interpretation": {
                    "r_reachable": "D1 r-reaches D2 means D1's value can affect D2's optimal action",
                    "s_reachable": "D1 s-reaches D2 means D1's action can strategically influence D2",
                },
            },
        }

    except Exception as e:
        return {
            "summary": f"Error: {str(e)}",
            "details": {"error": str(e)},
        }
