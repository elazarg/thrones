"""Nash equilibrium analysis plugin powered by Gambit/pygambit."""
from __future__ import annotations

import importlib.util
from collections.abc import Mapping
from itertools import product
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from app.core.registry import AnalysisResult, registry
from app.models.game import Game

if TYPE_CHECKING:
    import pygambit as gbt

PYGAMBIT_AVAILABLE = importlib.util.find_spec("pygambit") is not None
if PYGAMBIT_AVAILABLE:
    import pygambit as gbt
else:  # pragma: no cover - defensive assignment for type-checkers
    gbt = None


class NashEquilibrium(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    description: str
    behavior_profile: dict[str, dict[str, float]]
    outcomes: dict[str, float]
    strategies: dict[str, dict[str, float]]
    payoffs: dict[str, float]


class NashEquilibriumPlugin:
    name = "Nash Equilibrium"
    description = "Enumerates Nash equilibria using Gambit's enummixed solver."
    applicable_to: tuple[str, ...] = ("extensive", "strategic")
    continuous = True

    def can_run(self, game: Game) -> bool:  # noqa: D401 - interface parity
        return PYGAMBIT_AVAILABLE

    def run(self, game: Game, config: dict | None = None) -> AnalysisResult:
        if not PYGAMBIT_AVAILABLE:
            msg = "pygambit is not installed; install pygambit to run this analysis"
            raise RuntimeError(msg)

        gambit_game = self._to_gambit_table(game)
        result = gbt.nash.enummixed_solve(gambit_game, rational=False)
        equilibria = [
            self._to_equilibrium(gambit_game, eq).model_dump()
            for eq in result.equilibria
        ]
        summary = self.summarize(AnalysisResult(summary="", details={"equilibria": equilibria}))
        return AnalysisResult(
            summary=summary,
            details={"equilibria": equilibria, "solver": "gambit-enummixed"},
        )

    def summarize(self, result: AnalysisResult) -> str:  # noqa: D401 - interface parity
        equilibria = result.details.get("equilibria", [])
        count = len(equilibria)
        if count == 0:
            return "No Nash equilibria"
        if count == 1:
            return "1 Nash equilibrium (Gambit)"
        return f"{count} Nash equilibria (Gambit)"

    def _to_gambit_table(self, game: Game) -> "gbt.Game":
        strategies = self._enumerate_strategies(game)
        gambit_game = gbt.Game.new_table([len(strats) for strats in strategies.values()])
        gambit_game.title = game.title

        for player_index, player_name in enumerate(game.players):
            player = gambit_game.players[player_index]
            player.label = player_name
            for strat_index, strategy in enumerate(strategies[player_name]):
                labels = [strategy[node_id] for node_id in sorted(strategy.keys())]
                player.strategies[strat_index].label = "/".join(labels) if labels else "No moves"

        for profile_indices in product(*[range(len(strategies[player])) for player in game.players]):
            profile = {
                player: strategies[player][idx]
                for player, idx in zip(game.players, profile_indices, strict=True)
            }
            payoffs = self._resolve_payoffs(game, profile)
            outcome = gambit_game[profile_indices]
            for p_index, player_name in enumerate(game.players):
                outcome[gambit_game.players[p_index]] = payoffs.get(player_name, 0.0)

        return gambit_game

    def _enumerate_strategies(self, game: Game) -> dict[str, list[Mapping[str, str]]]:
        """Enumerate strategies respecting information sets.

        Nodes in the same information set must have the same action assigned,
        since the player cannot distinguish between them.
        """
        strategies: dict[str, list[Mapping[str, str]]] = {}
        for player in game.players:
            player_nodes = [node for node in game.nodes.values() if node.player == player]
            if not player_nodes:
                strategies[player] = [{}]
                continue

            # Group nodes by information set
            # Nodes with None info_set are treated as singleton sets (can distinguish)
            info_sets: dict[str, list] = {}
            for node in player_nodes:
                # Use node.id as key if no information set (singleton)
                key = node.information_set if node.information_set else f"_singleton_{node.id}"
                info_sets.setdefault(key, []).append(node)

            # For each info set, get available actions (use first node's actions)
            # All nodes in same info set should have same actions available
            info_set_keys = list(info_sets.keys())
            action_sets = []
            for key in info_set_keys:
                nodes_in_set = info_sets[key]
                # Use actions from first node (all nodes in info set should have same actions)
                action_sets.append([action.label for action in nodes_in_set[0].actions])

            # Enumerate strategies: one action per info set, applied to all nodes in that set
            player_strategies = []
            for action_combo in product(*action_sets):
                strategy: dict[str, str] = {}
                for key, action in zip(info_set_keys, action_combo, strict=True):
                    # Assign this action to ALL nodes in this info set
                    for node in info_sets[key]:
                        strategy[node.id] = action
                player_strategies.append(strategy)

            strategies[player] = player_strategies
        return strategies

    def _resolve_payoffs(
        self, game: Game, profile: Mapping[str, Mapping[str, str]]
    ) -> dict[str, float]:
        current = game.root
        visited: set[str] = set()

        while current and current not in visited:
            visited.add(current)
            node = game.nodes.get(current)
            if not node:
                break

            player_strategy = profile.get(node.player)
            if player_strategy is None:
                msg = f"Profile is missing strategy for player '{node.player}'"
                raise ValueError(msg)

            if node.id not in player_strategy:
                msg = f"Profile is missing action for node '{node.id}'"
                raise ValueError(msg)

            action_label = player_strategy[node.id]
            action = next((a for a in node.actions if a.label == action_label), None)
            if action is None or action.target is None:
                break
            if action.target in game.outcomes:
                return game.outcomes[action.target].payoffs
            current = action.target

        raise ValueError("Failed to reach a terminal outcome when simulating strategies")

    def _to_equilibrium(self, game: "gbt.Game", eq) -> NashEquilibrium:
        strategies: dict[str, dict[str, float]] = {}
        for strategy, probability in eq:
            player_label = strategy.player.label
            strategies.setdefault(player_label, {})[strategy.label] = float(probability)

        payoffs = {player.label: float(eq.payoff(player)) for player in game.players}

        # Generate human-readable description
        pure = all(
            p in (0.0, 1.0) for probs in strategies.values() for p in probs.values()
        )
        if pure:
            desc_parts = []
            for player, strats in strategies.items():
                chosen = max(strats, key=strats.get)
                desc_parts.append(f"{player} plays {chosen}")
            description = "Pure: " + ", ".join(desc_parts)
        else:
            description = "Mixed equilibrium"

        return NashEquilibrium(
            description=description,
            behavior_profile=strategies,
            outcomes=payoffs,
            strategies=strategies,
            payoffs=payoffs,
        )


registry.register_analysis(NashEquilibriumPlugin())
