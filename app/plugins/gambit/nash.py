"""Nash equilibrium analysis plugin powered by Gambit/pygambit."""
from __future__ import annotations

from threading import Event
from typing import TYPE_CHECKING

import pygambit as gbt
from pydantic import BaseModel, ConfigDict

from app.core.gambit_utils import (
    extensive_to_gambit_table,
    normal_form_to_gambit,
)
from app.core.registry import AnalysisResult, registry
from app.core.strategies import enumerate_strategies, resolve_payoffs
from app.models import AnyGame, NormalFormGame, ExtensiveFormGame

if TYPE_CHECKING:
    import pygambit as _gbt


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
        return True  # Always available when this module is loaded

    def run(self, game: AnyGame, config: dict | None = None) -> AnalysisResult:
        config = config or {}
        solver_type = config.get("solver", "exhaustive")
        max_equilibria = config.get("max_equilibria")
        cancel_event: Event | None = config.get("_cancel_event")

        def is_cancelled() -> bool:
            return cancel_event is not None and cancel_event.is_set()

        # Check for early cancellation
        if is_cancelled():
            return AnalysisResult(
                summary="Cancelled",
                details={"equilibria": [], "solver": "none", "exhaustive": False, "cancelled": True},
            )

        # Convert to Gambit game based on type
        if isinstance(game, NormalFormGame):
            gambit_game = normal_form_to_gambit(game)
        elif isinstance(game, ExtensiveFormGame):
            strategies = enumerate_strategies(game)
            gambit_game = extensive_to_gambit_table(game, strategies, resolve_payoffs)
        else:
            raise ValueError(f"Unsupported game type for Nash equilibrium analysis: {type(game)}")
        
        # Check after conversion (can be slow for large games)
        if is_cancelled():
            return AnalysisResult(
                summary="Cancelled",
                details={"equilibria": [], "solver": "none", "exhaustive": False, "cancelled": True},
            )

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
            # Note: simpdiv can fail on large games, fall back to logit
            result = None
            solver_name = "gambit-simpdiv"
            try:
                start = gambit_game.mixed_strategy_profile(rational=True)
                result = gbt.nash.simpdiv_solve(start)
            except Exception:
                # simpdiv failed (often on large games), try logit instead
                try:
                    result = gbt.nash.logit_solve(gambit_game)
                    solver_name = "gambit-logit"
                except Exception:
                    pass

            if result is None:
                # Both solvers failed - return empty result, not error
                return AnalysisResult(
                    summary="No approximate equilibrium found (game may be too large)",
                    details={"equilibria": [], "solver": "none", "exhaustive": False},
                )
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

        # Check after solver completes (solver calls are blocking)
        if is_cancelled():
            # Return partial results if we have any
            partial_eq = [
                self._to_equilibrium(gambit_game, eq).model_dump()
                for eq in result.equilibria
            ] if result and result.equilibria else []
            return AnalysisResult(
                summary=f"Cancelled (found {len(partial_eq)} equilibria)",
                details={
                    "equilibria": partial_eq,
                    "solver": solver_name,
                    "exhaustive": False,
                    "cancelled": True,
                },
            )

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

    def summarize(self, result: AnalysisResult, exhaustive: bool = True) -> str:  # noqa: D401
        equilibria = result.details.get("equilibria", [])
        count = len(equilibria)
        suffix = "" if exhaustive else "+"
        if count == 0:
            return "No Nash equilibria found"
        if count == 1:
            return f"1 Nash equilibrium{suffix}"
        return f"{count} Nash equilibria{suffix}"

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

    def _to_equilibrium(self, game: gbt.Game, eq) -> NashEquilibrium:
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
