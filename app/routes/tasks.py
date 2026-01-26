from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException

from app.core.registry import registry
from app.core.store import game_store
from app.core.tasks import task_manager, TaskStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["tasks"])


@router.post("/tasks")
def submit_task(
    game_id: str,
    plugin: str,
    owner: str = "anonymous",
    solver: str | None = None,
    max_equilibria: int | None = None,
) -> dict:
    game = game_store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")

    analysis_plugin = registry.get_analysis(plugin)
    if analysis_plugin is None:
        available = [p.name for p in registry.analyses()]
        raise HTTPException(status_code=400, detail=f"Unknown plugin: {plugin}. Available: {available}")

    if not analysis_plugin.can_run(game):
        raise HTTPException(status_code=400, detail=f"Plugin '{plugin}' cannot run on this game")

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
