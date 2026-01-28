from __future__ import annotations

import logging
import time

from fastapi import APIRouter

from app.core.errors import not_found
from app.core.store import game_store
from app.core.registry import AnalysisResult, registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["analyses"])

@router.get("/games/{game_id}/analyses", response_model=list[AnalysisResult])
def run_game_analyses(
    game_id: str,
    solver: str | None = None,
    max_equilibria: int | None = None,
) -> list[AnalysisResult]:
    """Run continuous analyses on a specific game.

    Args:
        game_id: The game identifier
        solver: Nash solver type: 'exhaustive' (default), 'quick', or 'pure'
        max_equilibria: Max equilibria to find (for 'quick' solver)
    """
    game = game_store.get(game_id)
    if game is None:
        raise not_found("Game", game_id)

    # Build config for plugins
    plugin_config: dict = {}
    if solver:
        plugin_config["solver"] = solver
    if max_equilibria:
        plugin_config["max_equilibria"] = max_equilibria

    logger.info("Running analyses for game: %s (config=%s)", game_id, plugin_config)
    results = []
    for plugin in registry.analyses():
        if plugin.continuous and plugin.can_run(game):
            try:
                start_time = time.perf_counter()
                result = plugin.run(game, config=plugin_config if plugin_config else None)
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)

                # Add timing to result details
                timed_result = AnalysisResult(
                    summary=result.summary,
                    details={**result.details, "computation_time_ms": elapsed_ms},
                )
                results.append(timed_result)
                logger.info("Analysis complete: %s (%dms)", plugin.name, elapsed_ms)
            except Exception as e:
                logger.error("Analysis failed (%s): %s", plugin.name, e)
                # Sanitize error - include type but not potentially sensitive details
                results.append(AnalysisResult(
                    summary=f"{plugin.name}: error",
                    details={"error": f"Analysis failed: {type(e).__name__}"},
                ))
    return results

