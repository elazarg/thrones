"""Gambit Extensive Form (.efg) parser using pygambit.

Leverages pygambit's built-in EFG parser for robustness,
then converts to our Game model.
"""
from __future__ import annotations

import importlib.util
import io
import uuid
from typing import TYPE_CHECKING

from app.formats import register_format
from app.models.game import Action, DecisionNode, Game, Outcome

if TYPE_CHECKING:
    import pygambit as gbt

PYGAMBIT_AVAILABLE = importlib.util.find_spec("pygambit") is not None

if PYGAMBIT_AVAILABLE:
    import pygambit as gbt


def parse_efg(content: str, filename: str = "game.efg") -> Game:
    """Parse Gambit EFG format into Game model.

    Uses pygambit for parsing, then converts to our internal model.
    """
    if not PYGAMBIT_AVAILABLE:
        raise RuntimeError("pygambit is required to parse EFG files")

    # Parse with pygambit using StringIO since read_efg takes file-like objects
    gambit_game = gbt.read_efg(io.StringIO(content))

    # Convert to our model
    return _gambit_to_game(gambit_game, source_file=filename)


def _gambit_to_game(gambit_game: "gbt.Game", source_file: str = "") -> Game:
    """Convert a pygambit Game to our Game model."""
    # Extract players
    players = [p.label or f"Player{i+1}" for i, p in enumerate(gambit_game.players)]

    # Build nodes and outcomes
    nodes: dict[str, DecisionNode] = {}
    outcomes: dict[str, Outcome] = {}

    # Track node IDs
    node_id_map: dict[int, str] = {}  # pygambit node index -> our node ID
    outcome_id_map: dict[int, str] = {}  # pygambit outcome index -> our outcome ID

    # First pass: create outcome IDs for all terminal nodes
    for i, outcome in enumerate(gambit_game.outcomes):
        outcome_id = f"o_{i}"
        outcome_id_map[i] = outcome_id

        # Get payoffs
        payoffs = {}
        for j, player in enumerate(gambit_game.players):
            player_name = players[j]
            payoffs[player_name] = float(outcome[player])

        outcomes[outcome_id] = Outcome(
            label=outcome.label or f"Outcome {i+1}",
            payoffs=payoffs,
        )

    # Second pass: traverse tree and build decision nodes
    root_id = _traverse_node(
        gambit_game.root,
        players,
        nodes,
        outcomes,
        node_id_map,
        outcome_id_map,
    )

    return Game(
        id=str(uuid.uuid4()),
        title=gambit_game.title or source_file.replace(".efg", ""),
        players=players,
        root=root_id,
        nodes=nodes,
        outcomes=outcomes,
        version="v1",
        tags=["imported", "efg"],
    )


def _traverse_node(
    node: "gbt.Node",
    players: list[str],
    nodes: dict[str, DecisionNode],
    outcomes: dict[str, Outcome],
    node_id_map: dict[int, str],
    outcome_id_map: dict[int, str],
    counter: list[int] | None = None,
) -> str:
    """Recursively traverse pygambit tree and build our nodes."""
    if counter is None:
        counter = [0]

    # Check if terminal
    if node.is_terminal:
        # Return outcome ID
        outcome = node.outcome
        if outcome is not None:
            # Find outcome index
            for i, o in enumerate(node.game.outcomes):
                if o == outcome:
                    return outcome_id_map[i]
        # No outcome assigned - create default
        outcome_id = f"o_terminal_{counter[0]}"
        counter[0] += 1
        outcomes[outcome_id] = Outcome(
            label=f"Terminal {counter[0]}",
            payoffs={p: 0.0 for p in players},
        )
        return outcome_id

    # Decision or chance node
    node_id = f"n_{counter[0]}"
    counter[0] += 1
    node_id_map[id(node)] = node_id

    # Get player - check if this is a chance node via player.is_chance
    player = node.player
    is_chance = player is not None and hasattr(player, 'is_chance') and player.is_chance

    if is_chance:
        # Chance node - we'll treat as a special player "Chance"
        player_name = "Chance"
    else:
        player_idx = list(node.game.players).index(player)
        player_name = players[player_idx]

    # Get actions
    actions = []
    infoset = node.infoset

    for action_idx, action in enumerate(infoset.actions):
        # Find child node for this action (use index, not action object)
        child_node = node.children[action_idx]

        # Recursively process child
        target_id = _traverse_node(
            child_node,
            players,
            nodes,
            outcomes,
            node_id_map,
            outcome_id_map,
            counter,
        )

        # Get action probability if chance node
        probability = None
        if is_chance:
            probability = float(infoset.actions[action])

        actions.append(Action(
            label=action.label or f"Action {len(actions)+1}",
            target=target_id,
            probability=probability,
        ))

    # Create node
    info_set_id = None
    if not is_chance and infoset is not None:
        info_set_id = f"h_{infoset.label}" if infoset.label else None

    nodes[node_id] = DecisionNode(
        id=node_id,
        player=player_name,
        actions=actions,
        information_set=info_set_id,
    )

    return node_id


def serialize_efg(game: Game) -> str:
    """Serialize Game model to EFG format.

    Note: This is a simplified serializer. For full compatibility,
    use pygambit's native serialization.
    """
    lines = []

    # Header
    player_list = " ".join(f'"{p}"' for p in game.players)
    lines.append(f'EFG 2 R "{game.title}" {{ {player_list} }}')
    lines.append("")

    # We would need to traverse the tree and output nodes
    # This is complex - for now, raise NotImplementedError
    raise NotImplementedError(
        "EFG serialization not yet implemented. "
        "Use pygambit directly for serialization."
    )


# Register format
register_format(".efg", parse_efg, None)  # No serializer yet
