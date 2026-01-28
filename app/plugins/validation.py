"""Validation plugin - checks game structure for errors and warnings."""
from __future__ import annotations

from app.core.registry import AnalysisResult
from app.dependencies import get_registry
from app.models import AnyGame, NormalFormGame, ExtensiveFormGame


class ValidationPlugin:
    """Validates game structure and reports errors/warnings."""

    name = "Validation"
    description = "Checks game structure for errors and warnings"
    applicable_to: tuple[str, ...] = ("extensive", "strategic")
    continuous = True

    def can_run(self, game: AnyGame) -> bool:  # noqa: D401
        """Validation can always run."""
        return True

    def run(self, game: AnyGame, config: dict | None = None) -> AnalysisResult:
        """Run validation checks on the game."""
        if isinstance(game, NormalFormGame):
            return self._validate_normal_form(game)
        elif isinstance(game, ExtensiveFormGame):
            return self._validate_extensive_form(game)
        else:
            raise ValueError(f"Unsupported game type for validation: {type(game)}")
        
    def _validate_normal_form(self, game: NormalFormGame) -> AnalysisResult:
        """Validate a normal form game."""
        errors: list[str] = []
        warnings: list[str] = []

        # Check: Exactly 2 players
        if len(game.players) != 2:
            errors.append(f"Normal form requires exactly 2 players, got {len(game.players)}")

        # Check: Strategy counts match payoff dimensions
        num_rows = len(game.strategies[0])
        num_cols = len(game.strategies[1])

        if len(game.payoffs) != num_rows:
            errors.append(
                f"Payoff matrix has {len(game.payoffs)} rows, expected {num_rows}"
            )
        else:
            for i, row in enumerate(game.payoffs):
                if len(row) != num_cols:
                    errors.append(
                        f"Payoff row {i} has {len(row)} columns, expected {num_cols}"
                    )

        # Check: At least one strategy per player
        if num_rows < 1:
            errors.append("Player 1 has no strategies")
        if num_cols < 1:
            errors.append("Player 2 has no strategies")

        summary = self.summarize(
            AnalysisResult(summary="", details={"errors": errors, "warnings": warnings})
        )
        return AnalysisResult(
            summary=summary,
            details={"errors": errors, "warnings": warnings},
        )

    def _validate_extensive_form(self, game: ExtensiveFormGame) -> AnalysisResult:
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

    def _find_reachable(self, game: ExtensiveFormGame) -> set[str]:
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


get_registry().register_analysis(ValidationPlugin())
