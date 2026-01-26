"""Dominance analysis plugin - identifies strictly dominated strategies."""
from __future__ import annotations

from itertools import product
from typing import Mapping, Any

from pydantic import BaseModel, ConfigDict

from app.core.registry import AnalysisResult, registry
from app.core.strategies import enumerate_strategies, resolve_payoff
from app.models import AnyGame, NormalFormGame, ExtensiveFormGame


class DominatedStrategy(BaseModel):
    """A dominated strategy with details."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    player: str
    dominated: str  # The dominated strategy label
    dominator: str  # The strategy that dominates it
    dominated_at_node: str  # Node ID where the dominated action is taken (or strategy name for NFG)


class DominancePlugin:
    """Identifies strictly dominated strategies in the game."""

    name = "Dominance"
    description = "Identifies strictly dominated strategies"
    applicable_to: tuple[str, ...] = ("extensive", "strategic")
    continuous = True

    def can_run(self, game: AnyGame) -> bool:  # noqa: D401
        """Check if dominance analysis can run."""
        return len(game.players) >= 2

    def run(self, game: AnyGame, config: dict | None = None) -> AnalysisResult:
        """Run dominance analysis."""
        if isinstance(game, NormalFormGame):
            return self._run_normal_form(game)
        elif isinstance(game, ExtensiveFormGame):
            return self._run_extensive_form(game)
        else:
            raise ValueError(f"Unsupported game type for dominance analysis: {type(game)}")
        
    def _run_normal_form(self, game: NormalFormGame) -> AnalysisResult:
        """Run dominance analysis on a normal form game."""
        dominated: list[dict[str, Any]] = []

        # Check row player (player 0) strategies
        num_rows = len(game.strategies[0])
        num_cols = len(game.strategies[1])

        for i in range(num_rows):
            for j in range(num_rows):
                if i == j:
                    continue
                # Check if strategy j dominates strategy i for row player
                if all(
                    game.payoffs[j][col][0] > game.payoffs[i][col][0]
                    for col in range(num_cols)
                ):
                    dominated.append(
                        DominatedStrategy(
                            player=game.players[0],
                            dominated=game.strategies[0][i],
                            dominator=game.strategies[0][j],
                            dominated_at_node=game.strategies[0][i],
                        ).model_dump()
                    )
                    break

        # Check column player (player 1) strategies
        for i in range(num_cols):
            for j in range(num_cols):
                if i == j:
                    continue
                # Check if strategy j dominates strategy i for column player
                if all(
                    game.payoffs[row][j][1] > game.payoffs[row][i][1]
                    for row in range(num_rows)
                ):
                    dominated.append(
                        DominatedStrategy(
                            player=game.players[1],
                            dominated=game.strategies[1][i],
                            dominator=game.strategies[1][j],
                            dominated_at_node=game.strategies[1][i],
                        ).model_dump()
                    )
                    break

        summary = self.summarize(
            AnalysisResult(summary="", details={"dominated_strategies": dominated})
        )
        return AnalysisResult(
            summary=summary,
            details={"dominated_strategies": dominated},
        )

    def _run_extensive_form(self, game: ExtensiveFormGame, config: dict | None = None) -> AnalysisResult:
        """Run dominance analysis."""
        dominated: list[dict[str, Any]] = []

        # Enumerate all strategies for each player
        strategies = enumerate_strategies(game)

        # For each player, check for dominated strategies
        for player in game.players:
            player_strategies = strategies[player]
            if len(player_strategies) < 2:
                continue

            # Get other players for opponent strategy combinations
            other_players = [p for p in game.players if p != player]

            # Compare each pair of strategies
            for i, strat1 in enumerate(player_strategies):
                for j, strat2 in enumerate(player_strategies):
                    if i == j:
                        continue

                    # Check if strat2 strictly dominates strat1
                    if self._is_strictly_dominated(
                        game, player, strat1, strat2, other_players, strategies
                    ):
                        # Find which action differs
                        for node_id in strat1:
                            if strat1[node_id] != strat2[node_id]:
                                dominated.append(
                                    DominatedStrategy(
                                        player=player,
                                        dominated=strat1[node_id],
                                        dominator=strat2[node_id],
                                        dominated_at_node=node_id,
                                    ).model_dump()
                                )
                                break
                        break  # Found dominator, move to next strategy

        # Remove duplicates
        seen = set()
        unique_dominated = []
        for d in dominated:
            key = (d["player"], d["dominated"], d["dominated_at_node"])
            if key not in seen:
                seen.add(key)
                unique_dominated.append(d)

        summary = self.summarize(
            AnalysisResult(summary="", details={"dominated_strategies": unique_dominated})
        )
        return AnalysisResult(
            summary=summary,
            details={"dominated_strategies": unique_dominated},
        )

    def summarize(self, result: AnalysisResult) -> str:  # noqa: D401
        """Generate one-line summary."""
        dominated = result.details.get("dominated_strategies", [])
        if not dominated:
            return "No dominated strategies"
        if len(dominated) == 1:
            d = dominated[0]
            return f"Dom: {d['player']}.{d['dominated']}"
        return f"{len(dominated)} dominated strategies"

    def _is_strictly_dominated(
        self,
        game: ExtensiveFormGame,
        player: str,
        strat1: Mapping[str, str],
        strat2: Mapping[str, str],
        other_players: list[str],
        all_strategies: dict[str, list[Mapping[str, str]]],
    ) -> bool:
        """Check if strat2 strictly dominates strat1 for the given player."""
        # Generate all opponent strategy combinations
        opponent_strat_lists = [all_strategies[p] for p in other_players]
        if not opponent_strat_lists:
            return False

        for opponent_combo in product(*opponent_strat_lists):
            opponent_profile = dict(zip(other_players, opponent_combo, strict=True))

            # Build full profiles
            profile1 = {player: strat1, **opponent_profile}
            profile2 = {player: strat2, **opponent_profile}

            try:
                payoff1 = resolve_payoff(game, player, profile1)
                payoff2 = resolve_payoff(game, player, profile2)
            except ValueError:
                # If we can't resolve, skip this comparison
                return False

            # For strict dominance, strat2 must be strictly better in ALL cases
            if payoff2 <= payoff1:
                return False

        return True


registry.register_analysis(DominancePlugin())
