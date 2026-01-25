"""Conversions between extensive form and normal form games."""
from __future__ import annotations

import uuid
from collections.abc import Mapping
from itertools import product
from typing import TYPE_CHECKING

from app.conversions.registry import Conversion, ConversionCheck, conversion_registry
from app.models.game import Action, DecisionNode, Game, Outcome
from app.models.normal_form import NormalFormGame

if TYPE_CHECKING:
    pass


# =============================================================================
# EFG -> NFG Conversion
# =============================================================================


def check_efg_to_nfg(game: Game | NormalFormGame) -> ConversionCheck:
    """Check if an extensive form game can be converted to normal form."""
    if isinstance(game, NormalFormGame):
        return ConversionCheck(possible=False, blockers=["Already normal form"])

    if len(game.players) != 2:
        return ConversionCheck(
            possible=False,
            blockers=[f"Matrix view requires exactly 2 players (game has {len(game.players)})"],
        )

    # Estimate strategy count WITHOUT enumerating (could be exponential!)
    num_profiles = _estimate_strategy_count(game)

    warnings = []
    blockers = []

    # Block conversion if too large (would hang or exhaust memory)
    if num_profiles > 10000:
        blockers.append(f"Too many strategy profiles ({num_profiles:,}) - conversion would be impractical")
        return ConversionCheck(possible=False, warnings=warnings, blockers=blockers)

    if num_profiles > 100:
        warnings.append(f"Large matrix: {num_profiles:,} strategy profiles")

    return ConversionCheck(possible=True, warnings=warnings)


def convert_efg_to_nfg(game: Game | NormalFormGame) -> NormalFormGame:
    """Convert an extensive form game to normal form (strategic form).

    Enumerates all pure strategies for each player and builds the payoff matrix.
    """
    if isinstance(game, NormalFormGame):
        return game

    if len(game.players) != 2:
        msg = f"Cannot convert to normal form: requires 2 players, game has {len(game.players)}"
        raise ValueError(msg)

    strategies = _enumerate_strategies(game)
    p1, p2 = game.players

    p1_strats = strategies[p1]
    p2_strats = strategies[p2]

    # Build payoff matrix
    payoffs: list[list[tuple[float, float]]] = []

    for p1_strat in p1_strats:
        row: list[tuple[float, float]] = []
        for p2_strat in p2_strats:
            profile = {p1: p1_strat, p2: p2_strat}
            outcome_payoffs = _resolve_payoffs(game, profile)
            row.append((outcome_payoffs.get(p1, 0.0), outcome_payoffs.get(p2, 0.0)))
        payoffs.append(row)

    # Create strategy labels
    def strategy_label(strat: Mapping[str, str]) -> str:
        if not strat:
            return "∅"
        labels = [strat[nid] for nid in sorted(strat.keys())]
        return "/".join(labels)

    p1_labels = [strategy_label(s) for s in p1_strats]
    p2_labels = [strategy_label(s) for s in p2_strats]

    return NormalFormGame(
        id=f"{game.id}-nfg",
        title=f"{game.title}",
        players=(p1, p2),
        strategies=(p1_labels, p2_labels),
        payoffs=payoffs,
        version=game.version,
        tags=[*[t for t in game.tags if t != "sequential"], "converted", "from-efg"],
    )


# =============================================================================
# NFG -> EFG Conversion
# =============================================================================


def check_nfg_to_efg(game: Game | NormalFormGame) -> ConversionCheck:
    """Check if a normal form game can be converted to extensive form."""
    if isinstance(game, Game):
        return ConversionCheck(possible=False, blockers=["Already extensive form"])

    return ConversionCheck(
        possible=True,
        warnings=["Simultaneity represented via information sets"],
    )


def convert_nfg_to_efg(game: Game | NormalFormGame) -> Game:
    """Convert a normal form game to extensive form.

    Creates a game tree where Player 1 moves first, and Player 2 moves second
    in an information set (can't observe P1's move), preserving simultaneity.
    """
    if isinstance(game, Game):
        return game

    p1, p2 = game.players
    p1_strats = game.strategies[0]
    p2_strats = game.strategies[1]

    nodes: dict[str, DecisionNode] = {}
    outcomes: dict[str, Outcome] = {}

    # Create P2's information set ID (all P2 nodes are in same info set)
    p2_info_set = "h_p2"

    # Create root node for P1
    p1_actions = []
    for i, p1_strat in enumerate(p1_strats):
        p2_node_id = f"n_p2_{i}"

        # Create P2's decision node
        p2_actions = []
        for j, p2_strat in enumerate(p2_strats):
            outcome_id = f"o_{i}_{j}"
            payoff_tuple = game.payoffs[i][j]
            outcomes[outcome_id] = Outcome(
                label=f"{p1_strat}, {p2_strat}",
                payoffs={p1: payoff_tuple[0], p2: payoff_tuple[1]},
            )
            p2_actions.append(Action(label=p2_strat, target=outcome_id))

        nodes[p2_node_id] = DecisionNode(
            id=p2_node_id,
            player=p2,
            actions=p2_actions,
            information_set=p2_info_set,
        )
        p1_actions.append(Action(label=p1_strat, target=p2_node_id))

    # Create root node
    root_id = "n_root"
    nodes[root_id] = DecisionNode(
        id=root_id,
        player=p1,
        actions=p1_actions,
        information_set=None,
    )

    return Game(
        id=f"{game.id}-efg",
        title=f"{game.title}",
        players=list(game.players),
        root=root_id,
        nodes=nodes,
        outcomes=outcomes,
        version=game.version,
        tags=[*[t for t in game.tags if t != "strategic-form"], "converted", "from-nfg"],
    )


# =============================================================================
# Helper functions (extracted from nash.py)
# =============================================================================


def _estimate_strategy_count(game: Game) -> int:
    """Estimate total strategy profile count WITHOUT enumerating.

    This is O(nodes) instead of O(product of all action counts), which
    could be exponential for games with many information sets.
    """
    player_strategy_counts: dict[str, int] = {}

    for player in game.players:
        player_nodes = [node for node in game.nodes.values() if node.player == player]
        if not player_nodes:
            player_strategy_counts[player] = 1
            continue

        # Group nodes by information set
        info_sets: dict[str, list[DecisionNode]] = {}
        for node in player_nodes:
            key = node.information_set if node.information_set else f"_singleton_{node.id}"
            info_sets.setdefault(key, []).append(node)

        # Count = product of action counts for each info set
        count = 1
        for key, nodes_in_set in info_sets.items():
            num_actions = len(nodes_in_set[0].actions)
            count *= num_actions
            # Early exit if count is already huge
            if count > 10_000_000:
                break
        player_strategy_counts[player] = count

    # Total profiles = product of each player's strategy count
    total = 1
    for count in player_strategy_counts.values():
        total *= count
        if total > 10_000_000:
            return total  # Cap to avoid overflow
    return total


def _enumerate_strategies(game: Game) -> dict[str, list[Mapping[str, str]]]:
    """Enumerate all pure strategies for each player.

    A strategy is a complete plan: one action for each information set.
    Nodes in the same information set must have the same action assigned.
    """
    strategies: dict[str, list[Mapping[str, str]]] = {}

    for player in game.players:
        player_nodes = [node for node in game.nodes.values() if node.player == player]
        if not player_nodes:
            strategies[player] = [{}]
            continue

        # Group nodes by information set
        info_sets: dict[str, list[DecisionNode]] = {}
        for node in player_nodes:
            key = node.information_set if node.information_set else f"_singleton_{node.id}"
            info_sets.setdefault(key, []).append(node)

        # Get actions for each info set (use first node's actions)
        info_set_keys = list(info_sets.keys())
        action_sets = []
        for key in info_set_keys:
            nodes_in_set = info_sets[key]
            action_sets.append([action.label for action in nodes_in_set[0].actions])

        # Enumerate: one action per info set
        player_strategies: list[Mapping[str, str]] = []
        for action_combo in product(*action_sets):
            strategy: dict[str, str] = {}
            for key, action in zip(info_set_keys, action_combo, strict=True):
                for node in info_sets[key]:
                    strategy[node.id] = action
            player_strategies.append(strategy)

        strategies[player] = player_strategies

    return strategies


def _resolve_payoffs(
    game: Game, profile: Mapping[str, Mapping[str, str]]
) -> dict[str, float]:
    """Simulate a strategy profile to get terminal payoffs."""
    current = game.root
    visited: set[str] = set()

    while current and current not in visited:
        visited.add(current)
        node = game.nodes.get(current)
        if not node:
            break

        player_strategy = profile.get(node.player)
        if player_strategy is None:
            msg = f"Profile missing strategy for player '{node.player}'"
            raise ValueError(msg)

        if node.id not in player_strategy:
            msg = f"Profile missing action for node '{node.id}'"
            raise ValueError(msg)

        action_label = player_strategy[node.id]
        action = next((a for a in node.actions if a.label == action_label), None)
        if action is None or action.target is None:
            break
        if action.target in game.outcomes:
            return game.outcomes[action.target].payoffs
        current = action.target

    raise ValueError("Failed to reach terminal outcome")


# =============================================================================
# Registration
# =============================================================================


conversion_registry.register(
    Conversion(
        name="EFG to NFG",
        source_format="extensive",
        target_format="normal",
        can_convert=check_efg_to_nfg,
        convert=convert_efg_to_nfg,
    )
)

conversion_registry.register(
    Conversion(
        name="NFG to EFG",
        source_format="normal",
        target_format="extensive",
        can_convert=check_nfg_to_efg,
        convert=convert_nfg_to_efg,
    )
)
