"""Profile verification plugin - checks if a strategy profile is a Nash equilibrium."""
from __future__ import annotations

import importlib.util
from collections.abc import Mapping
from itertools import product
from typing import TYPE_CHECKING, Union

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


class VerifyProfilePlugin:
    """Verifies if a given strategy profile is a Nash equilibrium."""

    name = "Verify Profile"
    description = "Check if a candidate profile is a Nash equilibrium"
    applicable_to: tuple[str, ...] = ("extensive", "strategic")
    continuous = False  # Only runs when explicitly triggered with config

    def can_run(self, game: AnyGame) -> bool:  # noqa: D401 - interface parity
        return PYGAMBIT_AVAILABLE

    def run(self, game: AnyGame, config: dict | None = None) -> AnalysisResult:
        if not PYGAMBIT_AVAILABLE:
            msg = "pygambit is not installed; install pygambit to run this analysis"
            raise RuntimeError(msg)

        if not config or "profile" not in config:
            msg = "Profile verification requires a 'profile' in config"
            raise ValueError(msg)

        candidate_profile = config["profile"]
        # profile format: {"Player1": {"Strategy1": 0.5, "Strategy2": 0.5}, ...}

        # Convert to Gambit game based on type
        if isinstance(game, NormalFormGame):
            gambit_game = self._normal_form_to_gambit(game)
        else:
            gambit_game = self._to_gambit_table(game)

        # Create a mixed strategy profile
        profile = gambit_game.mixed_strategy_profile()

        # Set probabilities from candidate
        for player in gambit_game.players:
            player_strategies = candidate_profile.get(player.label, {})
            for strategy in player.strategies:
                prob = player_strategies.get(strategy.label, 0.0)
                profile[strategy] = prob

        # Normalize the profile (ensure probabilities sum to 1)
        profile.normalize()

        # Calculate regrets
        max_regret = float(profile.max_regret())
        is_equilibrium = max_regret < 1e-6  # Small tolerance for floating point

        # Get per-strategy regrets
        strategy_regrets: dict[str, dict[str, float]] = {}
        for player in gambit_game.players:
            strategy_regrets[player.label] = {}
            for strategy in player.strategies:
                strategy_regrets[player.label][strategy.label] = self._clean_float(
                    float(profile.strategy_regret(strategy))
                )

        # Get expected payoffs
        payoffs = {
            player.label: self._clean_float(float(profile.payoff(player)))
            for player in gambit_game.players
        }

        if is_equilibrium:
            summary = "Profile is a Nash equilibrium"
        else:
            summary = f"Not an equilibrium (max regret: {max_regret:.4f})"

        return AnalysisResult(
            summary=summary,
            details={
                "is_equilibrium": is_equilibrium,
                "max_regret": self._clean_float(max_regret),
                "strategy_regrets": strategy_regrets,
                "payoffs": payoffs,
            },
        )

    def _clean_float(self, value: float, precision: int = 10) -> float:
        """Round floats to avoid floating point errors."""
        rounded = round(value, precision)
        if abs(rounded) < 1e-9:
            return 0.0
        return rounded

    def _normal_form_to_gambit(self, game: NormalFormGame) -> "gbt.Game":
        """Convert a NormalFormGame to a Gambit strategic form game."""
        num_rows = len(game.strategies[0])
        num_cols = len(game.strategies[1])

        gambit_game = gbt.Game.new_table([num_rows, num_cols])
        gambit_game.title = game.title

        for player_index, player_name in enumerate(game.players):
            player = gambit_game.players[player_index]
            player.label = player_name
            for strat_index, strat_name in enumerate(game.strategies[player_index]):
                player.strategies[strat_index].label = strat_name

        for row in range(num_rows):
            for col in range(num_cols):
                outcome = gambit_game[row, col]
                payoffs = game.payoffs[row][col]
                outcome[gambit_game.players[0]] = payoffs[0]
                outcome[gambit_game.players[1]] = payoffs[1]

        return gambit_game

    def _to_gambit_table(self, game: Game) -> "gbt.Game":
        """Convert extensive form game to Gambit strategic form."""
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
        """Enumerate strategies respecting information sets."""
        strategies: dict[str, list[Mapping[str, str]]] = {}
        for player in game.players:
            player_nodes = [node for node in game.nodes.values() if node.player == player]
            if not player_nodes:
                strategies[player] = [{}]
                continue

            info_sets: dict[str, list] = {}
            for node in player_nodes:
                key = node.information_set if node.information_set else f"_singleton_{node.id}"
                info_sets.setdefault(key, []).append(node)

            info_set_keys = list(info_sets.keys())
            action_sets = []
            for key in info_set_keys:
                nodes_in_set = info_sets[key]
                action_sets.append([action.label for action in nodes_in_set[0].actions])

            player_strategies = []
            for action_combo in product(*action_sets):
                strategy: dict[str, str] = {}
                for key, action in zip(info_set_keys, action_combo, strict=True):
                    for node in info_sets[key]:
                        strategy[node.id] = action
                player_strategies.append(strategy)

            strategies[player] = player_strategies
        return strategies

    def _resolve_payoffs(
        self, game: Game, profile: Mapping[str, Mapping[str, str]]
    ) -> dict[str, float]:
        """Resolve payoffs for a strategy profile."""
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


registry.register_analysis(VerifyProfilePlugin())
