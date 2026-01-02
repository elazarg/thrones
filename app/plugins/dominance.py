"""Dominance analysis plugin - identifies strictly dominated strategies."""
from __future__ import annotations

from collections.abc import Mapping
from itertools import product
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.registry import AnalysisResult, registry
from app.models.game import Game


class DominatedStrategy(BaseModel):
    """A dominated strategy with details."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    player: str
    dominated: str  # The dominated strategy label
    dominator: str  # The strategy that dominates it
    dominated_at_node: str  # Node ID where the dominated action is taken


class DominancePlugin:
    """Identifies strictly dominated strategies in the game."""

    name = "Dominance"
    description = "Identifies strictly dominated strategies"
    applicable_to: tuple[str, ...] = ("extensive", "strategic")
    continuous = True

    def can_run(self, game: Game) -> bool:  # noqa: D401
        """Check if dominance analysis can run."""
        return len(game.players) >= 2

    def run(self, game: Game, config: dict | None = None) -> AnalysisResult:
        """Run dominance analysis."""
        dominated: list[dict[str, Any]] = []

        # Enumerate all strategies for each player
        strategies = self._enumerate_strategies(game)

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

    def _enumerate_strategies(
        self, game: Game
    ) -> dict[str, list[Mapping[str, str]]]:
        """Enumerate all pure strategies respecting information sets.

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
            info_sets: dict[str, list] = {}
            for node in player_nodes:
                key = node.information_set if node.information_set else f"_singleton_{node.id}"
                info_sets.setdefault(key, []).append(node)

            # For each info set, get available actions
            info_set_keys = list(info_sets.keys())
            action_sets = []
            for key in info_set_keys:
                nodes_in_set = info_sets[key]
                action_sets.append([action.label for action in nodes_in_set[0].actions])

            # Enumerate strategies: one action per info set
            player_strategies = []
            for action_combo in product(*action_sets):
                strategy: dict[str, str] = {}
                for key, action in zip(info_set_keys, action_combo, strict=True):
                    for node in info_sets[key]:
                        strategy[node.id] = action
                player_strategies.append(strategy)

            strategies[player] = player_strategies
        return strategies

    def _is_strictly_dominated(
        self,
        game: Game,
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
                payoff1 = self._resolve_payoff(game, player, profile1)
                payoff2 = self._resolve_payoff(game, player, profile2)
            except ValueError:
                # If we can't resolve, skip this comparison
                return False

            # For strict dominance, strat2 must be strictly better in ALL cases
            if payoff2 <= payoff1:
                return False

        return True

    def _resolve_payoff(
        self, game: Game, player: str, profile: Mapping[str, Mapping[str, str]]
    ) -> float:
        """Resolve the payoff for a player given a strategy profile."""
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
                return game.outcomes[action.target].payoffs.get(player, 0.0)
            current = action.target

        raise ValueError("Failed to reach a terminal outcome")


registry.register_analysis(DominancePlugin())
