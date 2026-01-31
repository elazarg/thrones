"""Export extensive-form game dicts to Gambit EFG format."""
from __future__ import annotations

from typing import Any


def export_to_efg(game: dict[str, Any]) -> str:
    """Convert an extensive-form game dict to Gambit EFG text format.

    EFG format reference: https://gambitproject.readthedocs.io/en/latest/formats.html

    Args:
        game: Dict with keys: players, title, root, nodes, outcomes.
              nodes[id] = {id, player, actions: [{label, target}], information_set?}
              outcomes[id] = {label, payoffs: {player: value}}

    Returns:
        EFG format string that can be parsed by Gambit/OpenSpiel.
    """
    lines = []

    players = game.get("players", [])
    nodes = game.get("nodes", {})
    outcomes = game.get("outcomes", {})
    root = game.get("root", "")
    title = game.get("title", "Game").replace('"', "'")

    # Header: EFG 2 R "Title" { "Player1" "Player2" ... }
    player_list = " ".join(f'"{p}"' for p in players)
    lines.append(f'EFG 2 R "{title}" {{ {player_list} }}')
    lines.append("")

    # Build player index (1-based for Gambit)
    player_idx = {name: i + 1 for i, name in enumerate(players)}

    # Track information sets per player
    infoset_counter: dict[int, int] = {i + 1: 0 for i in range(len(players))}
    infoset_map: dict[str, int] = {}

    # Track outcome numbers (1-based)
    outcome_counter = [0]  # Use list for mutability in nested function
    outcome_number_map: dict[str, int] = {}

    def get_infoset_number(player: int, infoset_name: str | None) -> int:
        """Get or create information set number for a player."""
        if infoset_name is None:
            # Singleton information set - create unique one
            infoset_counter[player] += 1
            return infoset_counter[player]

        key = f"{player}:{infoset_name}"
        if key not in infoset_map:
            infoset_counter[player] += 1
            infoset_map[key] = infoset_counter[player]
        return infoset_map[key]

    def get_outcome_number(outcome_id: str) -> int:
        """Get or create outcome number for a terminal node."""
        if outcome_id not in outcome_number_map:
            outcome_counter[0] += 1
            outcome_number_map[outcome_id] = outcome_counter[0]
        return outcome_number_map[outcome_id]

    def traverse(node_id: str) -> list[str]:
        """Recursively traverse and generate EFG lines."""
        result = []

        # Check if this is an outcome (terminal)
        if node_id in outcomes:
            outcome = outcomes[node_id]
            # Terminal node: t "label" outcome_number { payoffs }
            payoff_dict = outcome.get("payoffs", {})
            payoffs = ", ".join(str(payoff_dict.get(p, 0)) for p in players)
            label = outcome.get("label", node_id).replace('"', "'")
            outcome_num = get_outcome_number(node_id)
            result.append(f't "{label}" {outcome_num} "{label}" {{ {payoffs} }}')
            return result

        # Decision node
        node = nodes.get(node_id)
        if node is None:
            # Missing node - create dummy terminal
            outcome_num = get_outcome_number(f"missing_{node_id}")
            result.append(f't "" {outcome_num} "missing_{node_id}" {{ {", ".join("0" for _ in players)} }}')
            return result

        player_name = node.get("player", "")
        player = player_idx.get(player_name, 1)
        infoset = get_infoset_number(player, node.get("information_set"))
        actions = node.get("actions", [])
        action_labels = " ".join(f'"{a.get("label", "?").replace(chr(34), chr(39))}"' for a in actions)

        # Personal node: p "label" player infoset { actions } 0
        label = node.get("id", node_id).replace('"', "'")
        result.append(f'p "{label}" {player} {infoset} {{ {action_labels} }} 0')

        # Recursively add children
        for action in actions:
            target = action.get("target")
            if target:
                result.extend(traverse(target))
            else:
                # No target - create dummy terminal
                outcome_num = get_outcome_number(f"none_{node_id}_{action.get('label', '')}")
                result.append(f't "" {outcome_num} "none" {{ {", ".join("0" for _ in players)} }}')

        return result

    lines.extend(traverse(root))

    return "\n".join(lines)
