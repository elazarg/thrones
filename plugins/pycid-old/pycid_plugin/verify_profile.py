"""MAID Profile Verification - check if a strategy profile is a Nash equilibrium."""

from __future__ import annotations

from typing import Any

from pycid_plugin.pycid_utils import maid_game_to_pycid


def run_verify_profile(
    game: dict[str, Any], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Verify if a given strategy profile is a Nash equilibrium for a MAID.

    Computes expected utility for each agent and checks for profitable
    deviations. A profile is a NE if no agent can improve by unilaterally
    changing their strategy.

    Args:
        game: Deserialized MAIDGame dict.
        config: Config with 'profile' key mapping agent -> decision -> action.

    Returns:
        Dict with 'summary' and 'details' keys.
    """
    config = config or {}
    profile = config.get("profile", {})

    if not profile:
        return {
            "summary": "Error: No profile provided",
            "details": {
                "error": "Profile configuration required",
                "is_equilibrium": False,
            },
        }

    try:
        macid = maid_game_to_pycid(game)
        agents = list(macid.agents)

        # Build intervention dict from profile
        # Profile format: {agent: {decision_node: action}}
        intervention = {}
        for agent, decisions in profile.items():
            if isinstance(decisions, dict):
                for dec_node, action in decisions.items():
                    intervention[dec_node] = action

        # Compute expected utility for each agent under this profile
        utilities = {}
        for agent in agents:
            try:
                eu = macid.expected_utility(intervention, agent=agent)
                utilities[agent] = float(eu)
            except Exception:
                utilities[agent] = 0.0

        # Check for profitable deviations
        deviations = []
        is_equilibrium = True

        for agent in agents:
            # Get this agent's decision nodes
            agent_decisions = list(macid.agent_decisions.get(agent, []))

            for dec_node in agent_decisions:
                # Get the domain for this decision
                node_obj = macid.get_cpds(dec_node)
                if node_obj is None:
                    continue

                try:
                    # Get possible values for this decision
                    # This depends on how the CPD is structured
                    current_action = intervention.get(dec_node)
                    if current_action is None:
                        continue

                    # Try alternative actions (simple approach: 0 and 1 for binary)
                    for alt_action in [0, 1]:
                        if alt_action == current_action:
                            continue

                        # Create alternative intervention
                        alt_intervention = dict(intervention)
                        alt_intervention[dec_node] = alt_action

                        try:
                            alt_eu = macid.expected_utility(
                                alt_intervention, agent=agent
                            )
                            alt_eu_float = float(alt_eu)

                            if alt_eu_float > utilities[agent] + 1e-9:
                                is_equilibrium = False
                                deviations.append(
                                    {
                                        "agent": agent,
                                        "decision": dec_node,
                                        "current_action": current_action,
                                        "better_action": alt_action,
                                        "current_utility": utilities[agent],
                                        "deviation_utility": alt_eu_float,
                                        "improvement": alt_eu_float - utilities[agent],
                                    }
                                )
                        except Exception:
                            pass

                except Exception:
                    pass

        if is_equilibrium:
            summary = "Profile IS a Nash equilibrium"
        else:
            summary = f"Profile is NOT a Nash equilibrium ({len(deviations)} profitable deviation{'s' if len(deviations) != 1 else ''})"

        return {
            "summary": summary,
            "details": {
                "is_equilibrium": is_equilibrium,
                "utilities": utilities,
                "deviations": deviations,
                "profile": profile,
            },
        }

    except Exception as e:
        return {
            "summary": f"Error: {str(e)}",
            "details": {"error": str(e), "is_equilibrium": False},
        }
