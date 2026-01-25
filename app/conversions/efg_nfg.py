"""Conversions between extensive form and normal form games."""
from __future__ import annotations

import uuid
from collections.abc import Mapping

from app.conversions.registry import Conversion, ConversionCheck, conversion_registry
from app.core.strategies import enumerate_strategies, estimate_strategy_count, resolve_payoffs
from app.models.game import Action, DecisionNode, Game, Outcome
from app.models.normal_form import NormalFormGame


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
    num_profiles = estimate_strategy_count(game)

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

    strategies = enumerate_strategies(game)
    p1, p2 = game.players

    p1_strats = strategies[p1]
    p2_strats = strategies[p2]

    # Build payoff matrix
    payoffs: list[list[tuple[float, float]]] = []

    for p1_strat in p1_strats:
        row: list[tuple[float, float]] = []
        for p2_strat in p2_strats:
            profile = {p1: p1_strat, p2: p2_strat}
            outcome_payoffs = resolve_payoffs(game, profile)
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
