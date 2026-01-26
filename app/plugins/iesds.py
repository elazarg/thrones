"""IESDS plugin - Iterated Elimination of Strictly Dominated Strategies."""
from __future__ import annotations

from app.core.gambit_utils import (
    PYGAMBIT_AVAILABLE,
    extensive_to_gambit_table,
    gbt,
    normal_form_to_gambit,
)
from app.core.registry import AnalysisResult, registry
from app.core.strategies import enumerate_strategies, resolve_payoffs
from app.models import AnyGame
from app.models.extensive_form import ExtensiveFormGame
from app.models.normal_form import NormalFormGame


class IESDSPlugin:
    """Iteratively eliminates strictly dominated strategies."""

    name = "IESDS"
    description = "Iterated Elimination of Strictly Dominated Strategies"
    applicable_to: tuple[str, ...] = ("extensive", "strategic")
    continuous = True

    def can_run(self, game: AnyGame) -> bool:  # noqa: D401 - interface parity
        return PYGAMBIT_AVAILABLE

    def run(self, game: AnyGame, config: dict | None = None) -> AnalysisResult:
        if not PYGAMBIT_AVAILABLE:
            msg = "pygambit is not installed; install pygambit to run this analysis"
            raise RuntimeError(msg)

        # Convert to Gambit game based on type
        if isinstance(game, NormalFormGame):
            gambit_game = normal_form_to_gambit(game)
        else:
            strategies = enumerate_strategies(game)
            gambit_game = extensive_to_gambit_table(game, strategies, resolve_payoffs)

        # Start with full support (all strategies) - use game directly on first round
        support = gambit_game.strategy_support_profile()
        eliminated: list[dict[str, str]] = []
        rounds = 0

        while True:
            rounds += 1
            # Get strategies that survive elimination of strictly dominated strategies
            new_support = gbt.supports.undominated_strategies_solve(support, strict=True)

            # Check if any strategies were eliminated
            eliminated_this_round = []
            for player in gambit_game.players:
                for strategy in player.strategies:
                    # Strategy was in old support but not in new
                    if strategy in support and strategy not in new_support:
                        eliminated_this_round.append({
                            "player": player.label,
                            "strategy": strategy.label,
                            "round": rounds,
                        })

            if not eliminated_this_round:
                # No more eliminations possible - we've reached the fixed point
                break

            eliminated.extend(eliminated_this_round)
            support = new_support

            # Safety limit to prevent infinite loops
            if rounds > 100:
                break

        # Get surviving strategies for summary
        surviving: dict[str, list[str]] = {}
        for player in gambit_game.players:
            surviving[player.label] = [
                s.label for s in player.strategies if s in support
            ]

        summary = self._summarize(eliminated, rounds, surviving)
        return AnalysisResult(
            summary=summary,
            details={
                "eliminated": eliminated,
                "rounds": rounds - 1 if rounds > 0 else 0,  # Don't count the final no-op round
                "surviving": surviving,
            },
        )

    def _summarize(
        self,
        eliminated: list[dict[str, str]],
        rounds: int,
        surviving: dict[str, list[str]],
    ) -> str:
        if not eliminated:
            return "No dominated strategies found"
        count = len(eliminated)
        rounds_actual = rounds - 1 if rounds > 1 else rounds
        if count == 1:
            e = eliminated[0]
            return f"Eliminated: {e['player']}.{e['strategy']}"
        return f"{count} strategies eliminated in {rounds_actual} round{'s' if rounds_actual != 1 else ''}"


registry.register_analysis(IESDSPlugin())
