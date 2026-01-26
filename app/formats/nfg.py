"""Gambit Normal Form (.nfg) parser using pygambit.

Parses NFG files into NormalFormGame for matrix visualization (2-player)
or converts to extensive form for tree visualization (3+ players).
"""
from __future__ import annotations

import importlib.util
import io
import uuid
from typing import TYPE_CHECKING, Union

from app.formats import register_format
from app.models.game import Action, DecisionNode, ExtensiveFormGame, Outcome
from app.models.normal_form import NormalFormGame

if TYPE_CHECKING:
    import pygambit as gbt

PYGAMBIT_AVAILABLE = importlib.util.find_spec("pygambit") is not None

if PYGAMBIT_AVAILABLE:
    import pygambit as gbt


def parse_nfg(content: str, filename: str = "game.nfg") -> Union[NormalFormGame, ExtensiveFormGame]:
    """Parse Gambit NFG format.

    For 2-player games: Returns NormalFormGame for matrix visualization.
    For 3+ players: Returns Game (extensive form) for tree visualization.
    """
    if not PYGAMBIT_AVAILABLE:
        raise RuntimeError("pygambit is required to parse NFG files")

    # Parse with pygambit using StringIO
    gambit_game = gbt.read_nfg(io.StringIO(content))

    # 2-player games get native normal form representation
    if len(gambit_game.players) == 2:
        return _nfg_to_normal_form(gambit_game, source_file=filename)

    # 3+ player games convert to extensive form for tree visualization
    return _nfg_to_extensive(gambit_game, source_file=filename)


def _nfg_to_normal_form(gambit_game: "gbt.Game", source_file: str = "") -> NormalFormGame:
    """Convert a 2-player normal form game to NormalFormGame model."""
    # Extract players
    players = tuple(
        p.label or f"Player{i+1}" for i, p in enumerate(gambit_game.players)
    )

    # Get strategies for each player
    strategies = tuple(
        [s.label or f"S{i+1}" for i, s in enumerate(player.strategies)]
        for player in gambit_game.players
    )

    # Build payoff matrix
    num_rows = len(strategies[0])
    num_cols = len(strategies[1])
    payoffs: list[list[tuple[float, float]]] = []

    for row_idx in range(num_rows):
        row_payoffs: list[tuple[float, float]] = []
        for col_idx in range(num_cols):
            # Get strategy profile
            profile_key = [
                gambit_game.players[0].strategies[row_idx],
                gambit_game.players[1].strategies[col_idx],
            ]
            # Get payoffs
            p1_payoff = float(gambit_game[profile_key][gambit_game.players[0]])
            p2_payoff = float(gambit_game[profile_key][gambit_game.players[1]])
            row_payoffs.append((p1_payoff, p2_payoff))
        payoffs.append(row_payoffs)

    return NormalFormGame(
        id=str(uuid.uuid4()),
        title=gambit_game.title or source_file.replace(".nfg", ""),
        players=players,  # type: ignore[arg-type]
        strategies=strategies,  # type: ignore[arg-type]
        payoffs=payoffs,
        version="v1",
        tags=["imported", "nfg", "strategic-form"],
    )


def _nfg_to_extensive(gambit_game: "gbt.Game", source_file: str = "") -> ExtensiveFormGame:
    """Convert a normal form game to extensive form representation.

    Creates a game tree where:
    - Player 1 moves first at the root
    - Player 2 moves at all second-level nodes (in one information set)
    - ... and so on for more players
    - Leaves contain the payoff outcomes
    """
    # Extract players
    players = [p.label or f"Player{i+1}" for i, p in enumerate(gambit_game.players)]

    if len(players) < 2:
        raise ValueError("NFG files must have at least 2 players")

    # Get strategies for each player
    strategies = []
    for player in gambit_game.players:
        strats = [s.label or f"S{i+1}" for i, s in enumerate(player.strategies)]
        strategies.append(strats)

    # Build the tree
    nodes: dict[str, DecisionNode] = {}
    outcomes: dict[str, Outcome] = {}

    # Create outcome for each strategy profile
    outcome_counter = 0

    def get_outcome_id(strategy_indices: tuple[int, ...]) -> str:
        """Get or create outcome for a strategy profile."""
        nonlocal outcome_counter
        outcome_id = f"o_{outcome_counter}"
        outcome_counter += 1

        # Get the strategic form outcome
        # Build strategy profile
        profile_key = []
        for player_idx, strat_idx in enumerate(strategy_indices):
            player = gambit_game.players[player_idx]
            profile_key.append(player.strategies[strat_idx])

        # Get payoffs from the contingency
        payoffs = {}
        for player_idx, player in enumerate(gambit_game.players):
            payoff = gambit_game[profile_key][player]
            payoffs[players[player_idx]] = float(payoff)

        # Create outcome label from strategy combination
        strat_labels = [
            strategies[i][idx] for i, idx in enumerate(strategy_indices)
        ]
        label = ", ".join(strat_labels)

        outcomes[outcome_id] = Outcome(label=label, payoffs=payoffs)
        return outcome_id

    # Build tree recursively
    node_counter = [0]

    def build_subtree(
        player_idx: int,
        strategy_prefix: tuple[int, ...],
        info_set_id: str | None,
    ) -> str:
        """Build subtree for remaining players."""
        if player_idx >= len(players):
            # Terminal - create outcome
            return get_outcome_id(strategy_prefix)

        node_id = f"n_{node_counter[0]}"
        node_counter[0] += 1

        player_name = players[player_idx]
        player_strategies = strategies[player_idx]

        # Create actions for each strategy
        actions = []
        for strat_idx, strat_label in enumerate(player_strategies):
            new_prefix = strategy_prefix + (strat_idx,)
            # Next player's info set (all nodes at that level share it)
            next_info_set = f"h_{player_idx + 1}" if player_idx + 1 < len(players) else None
            target = build_subtree(player_idx + 1, new_prefix, next_info_set)
            actions.append(Action(label=strat_label, target=target))

        nodes[node_id] = DecisionNode(
            id=node_id,
            player=player_name,
            actions=actions,
            information_set=info_set_id,
        )

        return node_id

    # Build from root (player 0, no info set at root)
    root_id = build_subtree(0, (), None)

    return ExtensiveFormGame(
        id=str(uuid.uuid4()),
        title=gambit_game.title or source_file.replace(".nfg", ""),
        players=players,
        root=root_id,
        nodes=nodes,
        outcomes=outcomes,
        version="v1",
        tags=["imported", "nfg", "strategic-form"],
    )


# Register format
register_format(".nfg", parse_nfg, None)
