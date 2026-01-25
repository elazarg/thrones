"""Nash equilibrium analysis plugin powered by Gambit/pygambit."""
from __future__ import annotations

import importlib.util
from collections.abc import Mapping
from itertools import product
from typing import TYPE_CHECKING, Union

from pydantic import BaseModel, ConfigDict

from app.core.registry import AnalysisResult, registry
from app.models.game import Game
from app.models.normal_form import NormalFormGame

# Type alias for any game type
AnyGame = Union[Game, NormalFormGame]

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
    description = "Computes Nash equilibria using Gambit solvers."
    applicable_to: tuple[str, ...] = ("extensive", "strategic")
    continuous = True

    # Solver configurations
    SOLVERS = {
        "exhaustive": {"solver": "enummixed", "description": "Find all equilibria (exhaustive)"},
        "quick": {"solver": "lcp", "description": "Find first equilibrium quickly"},
        "pure": {"solver": "enumpure", "description": "Find pure-strategy equilibria only"},
        "logit": {"solver": "logit", "description": "Find equilibrium by tracing logit QRE (fast for large games)"},
    }

    def can_run(self, game: AnyGame) -> bool:  # noqa: D401 - interface parity
        return PYGAMBIT_AVAILABLE

    def run(self, game: AnyGame, config: dict | None = None) -> AnalysisResult:
        if not PYGAMBIT_AVAILABLE:
            msg = "pygambit is not installed; install pygambit to run this analysis"
            raise RuntimeError(msg)

        config = config or {}
        solver_type = config.get("solver", "exhaustive")
        max_equilibria = config.get("max_equilibria")

        # Convert to Gambit game based on type
        if isinstance(game, NormalFormGame):
            gambit_game = self._normal_form_to_gambit(game)
        else:
            gambit_game = self._to_gambit_table(game)

        # Select solver based on config
        if solver_type == "quick":
            # Start with logit solver - traces QRE correspondence, fast for large games
            result = None
            solver_name = "gambit-logit"
            stop_after = max_equilibria if max_equilibria else 1

            try:
                result = gbt.nash.logit_solve(gambit_game)
            except Exception:
                pass

            # If we need more equilibria than logit found, try lcp
            if result is None or (stop_after > 1 and len(result.equilibria) < stop_after):
                try:
                    result = gbt.nash.lcp_solve(gambit_game, stop_after=stop_after, rational=False)
                    solver_name = "gambit-lcp"
                except Exception:
                    pass

            # Last resort: enummixed (exhaustive but slow)
            if result is None:
                result = gbt.nash.enummixed_solve(gambit_game, rational=False)
                solver_name = "gambit-enummixed"

            # Mark as exhaustive if we found fewer than requested
            # (meaning there are no more to find)
            exhaustive = len(result.equilibria) < stop_after
        elif solver_type == "pure":
            # enumpure_solve finds only pure-strategy equilibria
            result = gbt.nash.enumpure_solve(gambit_game)
            solver_name = "gambit-enumpure"
            exhaustive = True  # Exhaustive for pure strategies
        elif solver_type == "approximate":
            # simpdiv_solve finds approximate equilibrium via simplicial subdivision
            # Start from uniform mixed strategy profile (must be rational)
            start = gambit_game.mixed_strategy_profile(rational=True)
            result = gbt.nash.simpdiv_solve(start)
            solver_name = "gambit-simpdiv"
            exhaustive = False
        elif solver_type == "logit":
            # logit_solve traces the logit quantal response equilibrium (QRE) correspondence
            # Fast for large games, finds one equilibrium
            result = gbt.nash.logit_solve(gambit_game)
            solver_name = "gambit-logit"
            exhaustive = False
        else:
            # Default: enummixed_solve finds all mixed equilibria
            result = gbt.nash.enummixed_solve(gambit_game, rational=False)
            solver_name = "gambit-enummixed"
            exhaustive = True

        equilibria = [
            self._to_equilibrium(gambit_game, eq).model_dump()
            for eq in result.equilibria
        ]
        summary = self.summarize(
            AnalysisResult(summary="", details={"equilibria": equilibria}),
            exhaustive=exhaustive,
        )
        return AnalysisResult(
            summary=summary,
            details={
                "equilibria": equilibria,
                "solver": solver_name,
                "exhaustive": exhaustive,
            },
        )

    def _normal_form_to_gambit(self, game: NormalFormGame) -> "gbt.Game":
        """Convert a NormalFormGame to a Gambit strategic form game."""
        num_rows = len(game.strategies[0])
        num_cols = len(game.strategies[1])

        gambit_game = gbt.Game.new_table([num_rows, num_cols])
        gambit_game.title = game.title

        # Set player labels and strategy labels
        for player_index, player_name in enumerate(game.players):
            player = gambit_game.players[player_index]
            player.label = player_name
            for strat_index, strat_name in enumerate(game.strategies[player_index]):
                player.strategies[strat_index].label = strat_name

        # Set payoffs
        for row in range(num_rows):
            for col in range(num_cols):
                outcome = gambit_game[row, col]
                payoffs = game.payoffs[row][col]
                outcome[gambit_game.players[0]] = payoffs[0]
                outcome[gambit_game.players[1]] = payoffs[1]

        return gambit_game

    def summarize(self, result: AnalysisResult, exhaustive: bool = True) -> str:  # noqa: D401
        equilibria = result.details.get("equilibria", [])
        count = len(equilibria)
        suffix = "" if exhaustive else "+"
        if count == 0:
            return "No Nash equilibria found"
        if count == 1:
            return f"1 Nash equilibrium{suffix}"
        return f"{count} Nash equilibria{suffix}"

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

    def _clean_float(self, value: float, tolerance: float = 1e-6) -> float:
        """Round floats and snap to common rational values."""
        # Snap very small values to zero
        if abs(value) < tolerance:
            return 0.0

        # Snap to common fractions: 1/2, 1/3, 2/3, 1/4, 3/4, 1/5, 2/5, 3/5, 4/5, 1/6, 5/6
        common_fractions = [
            0.0, 1.0,
            0.5,  # 1/2
            1/3, 2/3,  # thirds
            0.25, 0.75,  # quarters
            0.2, 0.4, 0.6, 0.8,  # fifths
            1/6, 5/6,  # sixths
            1/8, 3/8, 5/8, 7/8,  # eighths
        ]
        for frac in common_fractions:
            if abs(value - frac) < tolerance:
                return frac

        # For integers, snap if close
        nearest_int = round(value)
        if abs(value - nearest_int) < tolerance:
            return float(nearest_int)

        # Otherwise round to 6 decimal places
        return round(value, 6)

    def _to_equilibrium(self, game: "gbt.Game", eq) -> NashEquilibrium:
        strategies: dict[str, dict[str, float]] = {}
        for strategy, probability in eq:
            player_label = strategy.player.label
            strategies.setdefault(player_label, {})[strategy.label] = self._clean_float(float(probability))

        payoffs = {player.label: self._clean_float(float(eq.payoff(player))) for player in game.players}

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
