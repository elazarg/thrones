"""Task management for long-running computations."""
from __future__ import annotations

import logging
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from threading import Event, Lock
from typing import Any, Callable

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a background task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class Task:
    """A background computation task."""

    id: str
    owner: str  # Session/client identifier
    status: TaskStatus
    plugin_name: str
    game_id: str
    config: dict = field(default_factory=dict)
    result: Any | None = None
    error: str | None = None
    cancel_event: Event = field(default_factory=Event)
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None

    # Internal (not serialized)
    _future: Future[None] | None = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "id": self.id,
            "owner": self.owner,
            "status": self.status.value,
            "plugin_name": self.plugin_name,
            "game_id": self.game_id,
            "config": self.config,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class TaskManager:
    """Manages background computation tasks."""

    def __init__(self, max_workers: int = 4):
        self._tasks: dict[str, Task] = {}
        self._lock = Lock()

        self._max_workers = max_workers
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=max_workers)

    def _new_executor(self) -> ThreadPoolExecutor:
        return ThreadPoolExecutor(max_workers=self._max_workers)

    def _ensure_executor(self) -> None:
        """
        Ensure there's a live executor.

        ThreadPoolExecutor exposes `_shutdown` internally; it's private but stable across CPython.
        We use it to detect if shutdown() already happened and recreate lazily.
        """
        ex = self._executor
        if getattr(ex, "_shutdown", False):
            self._executor = self._new_executor()

    def submit(
        self,
        owner: str,
        game_id: str,
        plugin_name: str,
        run_fn: Callable[[dict | None], Any],
        config: dict | None = None,
    ) -> str:
        task_id = str(uuid.uuid4())[:8]
        task = Task(
            id=task_id,
            owner=owner,
            status=TaskStatus.PENDING,
            plugin_name=plugin_name,
            game_id=game_id,
            config=config or {},
        )

        # Put task in registry first (so GET works immediately)
        with self._lock:
            self._tasks[task_id] = task
            self._ensure_executor()

            # Submit; if we race with shutdown, recreate and retry once.
            try:
                fut = self._executor.submit(self._run_task, task, run_fn)
            except RuntimeError:
                # Executor was shut down between _ensure_executor and submit.
                self._executor = self._new_executor()
                fut = self._executor.submit(self._run_task, task, run_fn)

            task._future = fut

        logger.info("Task %s submitted: %s on %s", task_id, plugin_name, game_id)
        return task_id

    def _run_task(self, task: Task, run_fn: Callable[[dict | None], Any]) -> None:
        # Mark running
        with self._lock:
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()

        logger.info("Task %s started", task.id)

        try:
            # Early cancellation
            if task.cancel_event.is_set():
                with self._lock:
                    task.completed_at = time.time()
                    task.status = TaskStatus.CANCELLED
                logger.info("Task %s cancelled before start", task.id)
                return

            # Give plugin access to cancellation
            config_with_cancel = {**(task.config or {}), "_cancel_event": task.cancel_event}

            result = run_fn(config_with_cancel)

            completed_at = time.time()
            cancelled = task.cancel_event.is_set()

            with self._lock:
                task.completed_at = completed_at
                task.result = result
                task.status = TaskStatus.CANCELLED if cancelled else TaskStatus.COMPLETED

            if cancelled:
                logger.info("Task %s cancelled during execution", task.id)
            else:
                logger.info("Task %s completed", task.id)

        except Exception as e:
            with self._lock:
                task.completed_at = time.time()
                task.error = f"{type(e).__name__}: {e}"
                task.status = TaskStatus.FAILED
            logger.exception("Task %s failed", task.id)

    def get(self, task_id: str) -> Task | None:
        with self._lock:
            return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False

            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return False

            task.cancel_event.set()

            # If still pending and in queue, try to cancel the Future.
            # If already running, this will return False, but the cancel_event
            # is still useful for cooperative cancellation in run_fn.
            if task._future is not None:
                task._future.cancel()

        logger.info("Task %s cancellation requested", task_id)
        return True

    def list_tasks(self, owner: str | None = None) -> list[Task]:
        with self._lock:
            tasks = list(self._tasks.values())
            if owner is not None:
                tasks = [t for t in tasks if t.owner == owner]
            return tasks

    def cleanup(self, max_age_seconds: int = 3600) -> int:
        now = time.time()
        removed_ids: list[str] = []

        with self._lock:
            for task_id, task in list(self._tasks.items()):
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    if task.completed_at and (now - task.completed_at) > max_age_seconds:
                        removed_ids.append(task_id)

            for task_id in removed_ids:
                del self._tasks[task_id]

        if removed_ids:
            logger.info("Cleaned up %d old tasks", len(removed_ids))
        return len(removed_ids)

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = True) -> None:
        """
        Shutdown executor.

        Defaults are chosen to be test-friendly:
        - wait=True: avoids background threads logging after pytest closes capture streams.
        - cancel_futures=True: prevents queued tasks from starting during shutdown.
        """
        with self._lock:
            ex = self._executor

        # ThreadPoolExecutor.shutdown is idempotent.
        ex.shutdown(wait=wait, cancel_futures=cancel_futures)


# Global task manager instance
task_manager = TaskManager()
