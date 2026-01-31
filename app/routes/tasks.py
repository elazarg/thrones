from __future__ import annotations

import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.analysis_helpers import resolve_game_for_plugin
from app.core.errors import not_found, plugin_unavailable
from app.core.registry import Registry
from app.core.store import GameStore
from app.core.tasks import TaskManager, TaskStatus
from app.dependencies import get_game_store, get_registry, get_task_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["tasks"])

# Type aliases for injected dependencies
GameStoreDep = Annotated[GameStore, Depends(get_game_store)]
RegistryDep = Annotated[Registry, Depends(get_registry)]
TaskManagerDep = Annotated[TaskManager, Depends(get_task_manager)]


@router.post("/tasks")
def submit_task(
    game_id: str,
    plugin: str,
    store: GameStoreDep,
    reg: RegistryDep,
    tasks: TaskManagerDep,
    owner: str = "anonymous",
    solver: str | None = None,
    max_equilibria: int | None = None,
) -> dict:
    """Submit an analysis task for async execution.

    Returns the created task in the same shape as GET /api/tasks/{id}.
    """
    analysis_plugin = reg.get_analysis(plugin)
    if analysis_plugin is None:
        available = [p.name for p in reg.analyses()]
        raise plugin_unavailable(plugin, available)

    # Get game (converting if necessary for this analysis)
    game = resolve_game_for_plugin(store, game_id, analysis_plugin)

    config: dict = {}
    if solver:
        config["solver"] = solver
    if max_equilibria:
        config["max_equilibria"] = max_equilibria

    def run_analysis(cfg: dict | None) -> dict:
        start = time.perf_counter()
        result = analysis_plugin.run(game, config=cfg)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "summary": result.summary,
            "details": {**result.details, "computation_time_ms": elapsed_ms},
        }

    task_id = tasks.submit(
        owner=owner,
        game_id=game_id,
        plugin_name=plugin,
        run_fn=run_analysis,
        config=config if config else None,
    )

    logger.info("Task submitted: %s (%s on %s)", task_id, plugin, game_id)

    # Return the full task object (same shape as GET /api/tasks/{id})
    task = tasks.get(task_id)
    return task.to_dict() if task else {"id": task_id, "status": "pending"}


@router.get("/tasks/{task_id}")
def get_task(task_id: str, tasks: TaskManagerDep) -> dict:
    """Get task status and result."""
    task = tasks.get(task_id)
    if task is None:
        raise not_found("Task", task_id)
    return task.to_dict()


@router.delete("/tasks/{task_id}")
def cancel_task(task_id: str, tasks: TaskManagerDep) -> dict:
    """Cancel a running or pending task.

    Returns the task state along with cancellation status.
    """
    task = tasks.get(task_id)
    if task is None:
        raise not_found("Task", task_id)

    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
        return {
            "cancelled": False,
            "reason": f"Task already {task.status.value}",
            "task": task.to_dict(),
        }

    cancelled = tasks.cancel(task_id)

    # Re-fetch to get updated state
    task = tasks.get(task_id)
    return {
        "cancelled": cancelled,
        "task": task.to_dict() if task else None,
    }


@router.get("/tasks")
def list_tasks(tasks: TaskManagerDep, owner: str | None = None) -> list[dict]:
    """List all tasks, optionally filtered by owner."""
    return [t.to_dict() for t in tasks.list_tasks(owner=owner)]
