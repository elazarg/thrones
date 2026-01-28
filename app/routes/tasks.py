from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException

from app.core.registry import registry
from app.core.store import game_store
from app.core.tasks import task_manager, TaskStatus
from app.conversions import conversion_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["tasks"])


def _get_game_for_analysis(game_id: str, analysis_plugin):
    """Get game for analysis, converting if necessary.

    Returns the game (possibly converted) that the plugin can run on.
    Raises HTTPException if no compatible game can be obtained.
    """
    game = game_store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")

    # If plugin can run on native game, use it
    if analysis_plugin.can_run(game):
        return game

    # Try to find a converted version the plugin can run on
    # Check what formats this plugin supports
    applicable_formats = getattr(analysis_plugin, 'applicable_to', [])

    for target_format in applicable_formats:
        if target_format == game.format_name:
            continue  # Already checked native format

        # Try to get converted game (uses cache if available)
        converted = game_store.get_converted(game_id, target_format)
        if converted and analysis_plugin.can_run(converted):
            logger.info("Using %s conversion for analysis %s on game %s",
                       target_format, analysis_plugin.name, game_id)
            return converted

    raise HTTPException(
        status_code=400,
        detail=f"Plugin '{analysis_plugin.name}' cannot run on this game (format: {game.format_name})"
    )


@router.post("/tasks")
def submit_task(
    game_id: str,
    plugin: str,
    owner: str = "anonymous",
    solver: str | None = None,
    max_equilibria: int | None = None,
) -> dict:
    analysis_plugin = registry.get_analysis(plugin)
    if analysis_plugin is None:
        available = [p.name for p in registry.analyses()]
        raise HTTPException(status_code=400, detail=f"Unknown plugin: {plugin}. Available: {available}")

    # Get game (converting if necessary for this analysis)
    game = _get_game_for_analysis(game_id, analysis_plugin)

    config: dict = {}
    if solver:
        config["solver"] = solver
    if max_equilibria:
        config["max_equilibria"] = max_equilibria

    def run_analysis(cfg: dict | None) -> dict:
        start = time.perf_counter()
        result = analysis_plugin.run(game, config=cfg)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {"summary": result.summary, "details": {**result.details, "computation_time_ms": elapsed_ms}}

    task_id = task_manager.submit(
        owner=owner,
        game_id=game_id,
        plugin_name=plugin,
        run_fn=run_analysis,
        config=config if config else None,
    )

    logger.info("Task submitted: %s (%s on %s)", task_id, plugin, game_id)
    return {"task_id": task_id, "status": "pending", "plugin": plugin, "game_id": game_id}


@router.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    task = task_manager.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return task.to_dict()


@router.delete("/tasks/{task_id}")
def cancel_task(task_id: str) -> dict:
    task = task_manager.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
        return {"task_id": task_id, "cancelled": False, "reason": f"Task already {task.status.value}"}

    return {"task_id": task_id, "cancelled": task_manager.cancel(task_id)}


@router.get("/tasks")
def list_tasks(owner: str | None = None) -> list[dict]:
    return [t.to_dict() for t in task_manager.list_tasks(owner=owner)]
