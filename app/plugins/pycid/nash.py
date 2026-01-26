"""Nash equilibrium analysis plugin for MAIDs powered by PyCID."""
from __future__ import annotations

from threading import Event
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from app.core.pycid_utils import maid_game_to_pycid, format_ne_result
from app.core.registry import AnalysisResult, registry
from app.models import AnyGame, MAIDGame

if TYPE_CHECKING:
    from pycid import MACID


class MAIDNashEquilibrium(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    description: str
    strategies: dict[str, dict[str, float]]
    behavior_profile: dict[str, dict[str, float]]


class MAIDNashEquilibriumPlugin:
    name = "MAID Nash Equilibrium"
    description = "Computes Nash equilibria for Multi-Agent Influence Diagrams using PyCID."
    applicable_to: tuple[str, ...] = ("maid",)
    continuous = True

    # Solver configurations
    SOLVERS = {
        "auto": {"description": "Auto-select solver based on game structure"},
        "enummixed": {"description": "Find all mixed equilibria (2-player only)"},
        "enumpure": {"description": "Find all pure-strategy equilibria"},
        "simpdiv": {"description": "Find one mixed equilibrium via simplicial subdivision"},
        "lcp": {"description": "Find equilibrium via linear complementarity (2-player only)"},
    }

    def can_run(self, game: AnyGame) -> bool:
        """Check if this plugin can analyze the given game."""
        return isinstance(game, MAIDGame)

    def run(self, game: AnyGame, config: dict | None = None) -> AnalysisResult:
        """Compute Nash equilibria for a MAID.

        Args:
            game: The MAIDGame to analyze.
            config: Optional configuration with 'solver' key.

        Returns:
            AnalysisResult with equilibria details.
        """
        if not isinstance(game, MAIDGame):
            return AnalysisResult(
                summary="Error: Not a MAID game",
                details={"error": "This plugin only supports MAID games"},
            )

        config = config or {}
        solver_type = config.get("solver", "auto")
        cancel_event: Event | None = config.get("_cancel_event")

        def is_cancelled() -> bool:
            return cancel_event is not None and cancel_event.is_set()

        # Check for early cancellation
        if is_cancelled():
            return AnalysisResult(
                summary="Cancelled",
                details={"equilibria": [], "solver": "none", "cancelled": True},
            )

        try:
            # Convert to PyCID MACID
            macid = maid_game_to_pycid(game)

            # Check after conversion
            if is_cancelled():
                return AnalysisResult(
                    summary="Cancelled",
                    details={"equilibria": [], "solver": "none", "cancelled": True},
                )

            # Determine solver
            solver_arg = None if solver_type == "auto" else solver_type

            # Compute Nash equilibria
            ne_list = macid.get_ne(solver=solver_arg)

            # Check after computation
            if is_cancelled():
                return AnalysisResult(
                    summary="Cancelled (partial results)",
                    details={"equilibria": [], "solver": solver_type, "cancelled": True},
                )

            # Format results
            equilibria = format_ne_result(ne_list, game)

            # Determine actual solver used
            solver_used = solver_type if solver_type != "auto" else "auto"

            summary = self.summarize(
                AnalysisResult(summary="", details={"equilibria": equilibria})
            )

            return AnalysisResult(
                summary=summary,
                details={
                    "equilibria": equilibria,
                    "solver": solver_used,
                    "exhaustive": solver_type in ("enummixed", "enumpure"),
                },
            )

        except Exception as e:
            return AnalysisResult(
                summary=f"Error: {str(e)}",
                details={"error": str(e), "equilibria": []},
            )

    def summarize(self, result: AnalysisResult, exhaustive: bool = True) -> str:
        """Generate a human-readable summary of the results."""
        equilibria = result.details.get("equilibria", [])
        count = len(equilibria)
        suffix = "" if exhaustive else "+"
        if count == 0:
            return "No Nash equilibria found"
        if count == 1:
            return f"1 Nash equilibrium{suffix}"
        return f"{count} Nash equilibria{suffix}"


# Register the plugin
registry.register_analysis(MAIDNashEquilibriumPlugin())
