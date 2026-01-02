"""Validation plugin - checks game structure for errors and warnings."""
from __future__ import annotations

from app.core.registry import AnalysisResult, registry
from app.models.game import Game


class ValidationPlugin:
    """Validates game structure and reports errors/warnings."""

    name = "Validation"
    description = "Checks game structure for errors and warnings"
    applicable_to: tuple[str, ...] = ("extensive", "strategic")
    continuous = True

    def can_run(self, game: Game) -> bool:  # noqa: D401
        """Validation can always run."""
        return True

    def run(self, game: Game, config: dict | None = None) -> AnalysisResult:
        """Run validation checks on the game."""
        errors: list[str] = []
        warnings: list[str] = []

        # Check: Root node exists
        if game.root not in game.nodes and game.root not in game.outcomes:
            errors.append(f"Root node '{game.root}' does not exist")

        # Check: All action targets point to valid nodes/outcomes
        for node_id, node in game.nodes.items():
            for action in node.actions:
                if action.target is None:
                    errors.append(f"Action '{action.label}' in node '{node_id}' has no target")
                elif action.target not in game.nodes and action.target not in game.outcomes:
                    errors.append(
                        f"Action '{action.label}' in node '{node_id}' "
                        f"points to non-existent target '{action.target}'"
                    )

        # Check: All outcomes have payoffs for all players
        for outcome_id, outcome in game.outcomes.items():
            for player in game.players:
                if player not in outcome.payoffs:
                    errors.append(
                        f"Outcome '{outcome_id}' missing payoff for player '{player}'"
                    )

        # Check: No orphan nodes (unreachable from root)
        reachable = self._find_reachable(game)
        for node_id in game.nodes:
            if node_id not in reachable:
                warnings.append(f"Node '{node_id}' is unreachable from root")
        for outcome_id in game.outcomes:
            if outcome_id not in reachable:
                warnings.append(f"Outcome '{outcome_id}' is unreachable from root")

        # Check: At least 2 players
        if len(game.players) < 2:
            warnings.append(f"Game has only {len(game.players)} player(s)")

        # Check: Each decision node has at least one action
        for node_id, node in game.nodes.items():
            if not node.actions:
                errors.append(f"Decision node '{node_id}' has no actions")

        summary = self.summarize(
            AnalysisResult(summary="", details={"errors": errors, "warnings": warnings})
        )
        return AnalysisResult(
            summary=summary,
            details={"errors": errors, "warnings": warnings},
        )

    def summarize(self, result: AnalysisResult) -> str:  # noqa: D401
        """Generate one-line summary."""
        errors = result.details.get("errors", [])
        warnings = result.details.get("warnings", [])

        if errors:
            return f"Invalid: {len(errors)} error(s)"
        if warnings:
            return f"Valid with {len(warnings)} warning(s)"
        return "Valid"

    def _find_reachable(self, game: Game) -> set[str]:
        """Find all nodes/outcomes reachable from root via BFS."""
        reachable: set[str] = set()
        queue = [game.root]

        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)

            node = game.nodes.get(current)
            if node:
                for action in node.actions:
                    if action.target and action.target not in reachable:
                        queue.append(action.target)

        return reachable


registry.register_analysis(ValidationPlugin())
