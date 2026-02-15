"""Gambit format parsers for EFG and NFG files.

Returns plain dicts matching the ExtensiveFormGame and NormalFormGame schemas,
suitable for JSON serialization over HTTP.
"""

from __future__ import annotations

import io
import uuid
from typing import Any

import pygambit as gbt


def parse_efg(content: str, filename: str = "game.efg") -> dict[str, Any]:
    """Parse Gambit EFG format into dict matching ExtensiveFormGame schema."""
    gambit_game = gbt.read_efg(io.StringIO(content))
    result = _gambit_efg_to_dict(gambit_game, source_file=filename)
    # Include the original EFG content for OpenSpiel and other tools
    result["efg_content"] = content
    return result


def parse_nfg(content: str, filename: str = "game.nfg") -> dict[str, Any]:
    """Parse Gambit NFG format.

    For 2-player games: Returns dict matching NormalFormGame schema.
    For 3+ players: Returns dict matching ExtensiveFormGame schema.
    """
    gambit_game = gbt.read_nfg(io.StringIO(content))

    if len(gambit_game.players) == 2:
        return _nfg_to_normal_form_dict(gambit_game, source_file=filename)

    return _nfg_to_extensive_dict(gambit_game, source_file=filename)


def _gambit_efg_to_dict(gambit_game: gbt.Game, source_file: str = "") -> dict[str, Any]:
    """Convert a pygambit ExtensiveFormGame to dict."""
    players = [p.label or f"Player{i+1}" for i, p in enumerate(gambit_game.players)]

    nodes: dict[str, dict[str, Any]] = {}
    outcomes: dict[str, dict[str, Any]] = {}

    node_id_map: dict[int, str] = {}
    outcome_id_map: dict[int, str] = {}

    # First pass: create outcomes
    for i, outcome in enumerate(gambit_game.outcomes):
        outcome_id = f"o_{i}"
        outcome_id_map[i] = outcome_id

        payoffs = {}
        for j, player in enumerate(gambit_game.players):
            player_name = players[j]
            payoffs[player_name] = float(outcome[player])

        outcomes[outcome_id] = {
            "label": outcome.label or f"Outcome {i+1}",
            "payoffs": payoffs,
        }

    # Second pass: traverse tree
    root_id = _traverse_efg_node(
        gambit_game.root,
        players,
        nodes,
        outcomes,
        node_id_map,
        outcome_id_map,
    )

    return {
        "format_name": "extensive",
        "id": str(uuid.uuid4()),
        "title": gambit_game.title or source_file.replace(".efg", ""),
        "players": players,
        "root": root_id,
        "nodes": nodes,
        "outcomes": outcomes,
        "tags": ["imported", "extensive"],
    }


def _traverse_efg_node(
    node: gbt.Node,
    players: list[str],
    nodes: dict[str, dict[str, Any]],
    outcomes: dict[str, dict[str, Any]],
    node_id_map: dict[int, str],
    outcome_id_map: dict[int, str],
    counter: list[int] | None = None,
) -> str:
    """Recursively traverse pygambit tree and build node dicts."""
    if counter is None:
        counter = [0]

    # Check if terminal
    if node.is_terminal:
        outcome = node.outcome
        if outcome is not None:
            for i, o in enumerate(node.game.outcomes):
                if o == outcome:
                    return outcome_id_map[i]
        # No outcome assigned - create default
        outcome_id = f"o_terminal_{counter[0]}"
        counter[0] += 1
        outcomes[outcome_id] = {
            "label": f"Terminal {counter[0]}",
            "payoffs": {p: 0.0 for p in players},
        }
        return outcome_id

    # Decision or chance node
    node_id = f"n_{counter[0]}"
    counter[0] += 1
    node_id_map[id(node)] = node_id

    player = node.player
    is_chance = player is not None and hasattr(player, "is_chance") and player.is_chance

    if is_chance:
        player_name = "Chance"
    else:
        player_idx = list(node.game.players).index(player)
        player_name = players[player_idx]

    actions = []
    infoset = node.infoset

    for action_idx, action in enumerate(infoset.actions):
        child_node = node.children[action_idx]

        target_id = _traverse_efg_node(
            child_node,
            players,
            nodes,
            outcomes,
            node_id_map,
            outcome_id_map,
            counter,
        )

        probability = None
        if is_chance:
            probability = float(infoset.actions[action])

        action_dict: dict[str, Any] = {
            "label": action.label or f"Action {len(actions)+1}",
            "target": target_id,
        }
        if probability is not None:
            action_dict["probability"] = probability
        actions.append(action_dict)

    # Information set
    info_set_id = None
    if not is_chance and infoset is not None:
        player_idx = list(node.game.players).index(player)
        infoset_idx = list(player.infosets).index(infoset)
        info_set_id = f"h_{player_idx}_{infoset_idx}"

    nodes[node_id] = {
        "id": node_id,
        "player": player_name,
        "actions": actions,
        "information_set": info_set_id,
    }

    return node_id


def _nfg_to_normal_form_dict(
    gambit_game: gbt.Game, source_file: str = ""
) -> dict[str, Any]:
    """Convert a 2-player normal form game to dict matching NormalFormGame schema."""
    players = tuple(
        p.label or f"Player{i+1}" for i, p in enumerate(gambit_game.players)
    )

    strategies = tuple(
        [s.label or f"S{i+1}" for i, s in enumerate(player.strategies)]
        for player in gambit_game.players
    )

    num_rows = len(strategies[0])
    num_cols = len(strategies[1])
    payoffs: list[list[list[float]]] = []

    for row_idx in range(num_rows):
        row_payoffs: list[list[float]] = []
        for col_idx in range(num_cols):
            profile_key = [
                gambit_game.players[0].strategies[row_idx],
                gambit_game.players[1].strategies[col_idx],
            ]
            p1_payoff = float(gambit_game[profile_key][gambit_game.players[0]])
            p2_payoff = float(gambit_game[profile_key][gambit_game.players[1]])
            row_payoffs.append([p1_payoff, p2_payoff])
        payoffs.append(row_payoffs)

    return {
        "format_name": "normal",
        "id": str(uuid.uuid4()),
        "title": gambit_game.title or source_file.replace(".nfg", ""),
        "players": list(players),
        "strategies": [list(s) for s in strategies],
        "payoffs": payoffs,
        "tags": ["imported", "nfg", "strategic-form"],
    }


def _nfg_to_extensive_dict(
    gambit_game: gbt.Game, source_file: str = ""
) -> dict[str, Any]:
    """Convert a normal form game to extensive form dict (for 3+ players)."""
    players = [p.label or f"Player{i+1}" for i, p in enumerate(gambit_game.players)]

    if len(players) < 2:
        raise ValueError("NFG files must have at least 2 players")

    strategies = []
    for player in gambit_game.players:
        strats = [s.label or f"S{i+1}" for i, s in enumerate(player.strategies)]
        strategies.append(strats)

    nodes: dict[str, dict[str, Any]] = {}
    outcomes: dict[str, dict[str, Any]] = {}

    outcome_counter = [0]
    node_counter = [0]

    def get_outcome_id(strategy_indices: tuple[int, ...]) -> str:
        """Get or create outcome for a strategy profile."""
        outcome_id = f"o_{outcome_counter[0]}"
        outcome_counter[0] += 1

        profile_key = []
        for player_idx, strat_idx in enumerate(strategy_indices):
            player = gambit_game.players[player_idx]
            profile_key.append(player.strategies[strat_idx])

        payoffs = {}
        for player_idx, player in enumerate(gambit_game.players):
            payoff = gambit_game[profile_key][player]
            payoffs[players[player_idx]] = float(payoff)

        strat_labels = [strategies[i][idx] for i, idx in enumerate(strategy_indices)]
        label = ", ".join(strat_labels)

        outcomes[outcome_id] = {"label": label, "payoffs": payoffs}
        return outcome_id

    def build_subtree(
        player_idx: int,
        strategy_prefix: tuple[int, ...],
        info_set_id: str | None,
    ) -> str:
        """Build subtree for remaining players."""
        if player_idx >= len(players):
            return get_outcome_id(strategy_prefix)

        node_id = f"n_{node_counter[0]}"
        node_counter[0] += 1

        player_name = players[player_idx]
        player_strategies = strategies[player_idx]

        actions = []
        for strat_idx, strat_label in enumerate(player_strategies):
            new_prefix = strategy_prefix + (strat_idx,)
            next_info_set = (
                f"h_{player_idx + 1}" if player_idx + 1 < len(players) else None
            )
            target = build_subtree(player_idx + 1, new_prefix, next_info_set)
            actions.append({"label": strat_label, "target": target})

        nodes[node_id] = {
            "id": node_id,
            "player": player_name,
            "actions": actions,
            "information_set": info_set_id,
        }

        return node_id

    root_id = build_subtree(0, (), None)

    return {
        "format_name": "extensive",
        "id": str(uuid.uuid4()),
        "title": gambit_game.title or source_file.replace(".nfg", ""),
        "players": players,
        "root": root_id,
        "nodes": nodes,
        "outcomes": outcomes,
        "tags": ["imported", "nfg", "strategic-form"],
    }
