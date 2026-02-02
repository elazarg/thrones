from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.analysis_helpers import try_resolve_game_for_plugin
from app.core.errors import not_found
from app.core.registry import AnalysisResult
from app.dependencies import GameStoreDep, RegistryDep

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["analyses"])


class AnalysisInfo(BaseModel):
    """Information about an available analysis plugin."""

    name: str
    description: str
    applicable_to: list[str]
    continuous: bool


class PluginAnalysisResult(BaseModel):
    """Analysis result with plugin attribution."""

    plugin_name: str
    result: AnalysisResult


@router.get("/analyses", response_model=list[AnalysisInfo])
def list_analyses(reg: RegistryDep) -> list[AnalysisInfo]:
    """List all available analysis plugins."""
    return [
        AnalysisInfo(
            name=plugin.name,
            description=plugin.description,
            applicable_to=list(plugin.applicable_to),
            continuous=plugin.continuous,
        )
        for plugin in reg.analyses()
    ]


@router.get("/games/{game_id}/analyses", response_model=list[PluginAnalysisResult])
def run_game_analyses(
    game_id: str,
    store: GameStoreDep,
    reg: RegistryDep,
    solver: str | None = None,
    max_equilibria: int | None = None,
) -> list[PluginAnalysisResult]:
    """Run continuous analyses on a specific game.

    Attempts format conversion if a plugin cannot run on the native game format.

    Args:
        game_id: The game identifier
        solver: Nash solver type: 'exhaustive' (default), 'quick', or 'pure'
        max_equilibria: Max equilibria to find (for 'quick' solver)
    """
    game = store.get(game_id)
    if game is None:
        raise not_found("Game", game_id)

    # Build config for plugins
    plugin_config: dict[str, Any] = {}
    if solver:
        plugin_config["solver"] = solver
    if max_equilibria:
        plugin_config["max_equilibria"] = max_equilibria

    logger.info("Running analyses for game: %s (config=%s)", game_id, plugin_config)
    results: list[PluginAnalysisResult] = []

    for plugin in reg.analyses():
        if not plugin.continuous:
            continue

        # Try to get a compatible game (with conversion fallback)
        compatible_game = try_resolve_game_for_plugin(store, game, plugin)
        if compatible_game is None:
            continue

        try:
            start_time = time.perf_counter()
            result = plugin.run(compatible_game, config=plugin_config if plugin_config else None)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            # Add timing to result details
            timed_result = AnalysisResult(
                summary=result.summary,
                details={**result.details, "computation_time_ms": elapsed_ms},
            )
            results.append(
                PluginAnalysisResult(
                    plugin_name=plugin.name,
                    result=timed_result,
                )
            )
            logger.info("Analysis complete: %s (%dms)", plugin.name, elapsed_ms)
        except Exception as e:
            logger.error("Analysis failed (%s): %s", plugin.name, e)
            # Sanitize error - include type but not potentially sensitive details
            results.append(
                PluginAnalysisResult(
                    plugin_name=plugin.name,
                    result=AnalysisResult(
                        summary=f"{plugin.name}: error",
                        details={"error": f"Analysis failed: {type(e).__name__}"},
                    ),
                )
            )

    return results
