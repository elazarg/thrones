"""Profile verification plugin - checks if a strategy profile is a Nash equilibrium."""
from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING, Union

from app.core.gambit_utils import extensive_to_gambit_table, normal_form_to_gambit
from app.core.registry import AnalysisResult, registry
from app.core.strategies import enumerate_strategies, resolve_payoffs
from app.models.game import ExtensiveFormGame
from app.models.normal_form import NormalFormGame

# Type alias for any game type
AnyGame = Union[ExtensiveFormGame, NormalFormGame]

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
            gambit_game = normal_form_to_gambit(game)
        else:
            strategies = enumerate_strategies(game)
            gambit_game = extensive_to_gambit_table(game, strategies, resolve_payoffs)

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


registry.register_analysis(VerifyProfilePlugin())
