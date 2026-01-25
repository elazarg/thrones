"""Task management for long-running computations."""
from __future__ import annotations

import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
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
    """Manages background computation tasks.

    Provides:
    - Non-blocking task submission
    - Task status tracking
    - Task cancellation
    - Automatic cleanup of old tasks
    """

    def __init__(self, max_workers: int = 4):
        """Initialize the task manager.

        Args:
            max_workers: Maximum concurrent background tasks.
        """
        self._tasks: dict[str, Task] = {}
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._max_workers = max_workers

    def submit(
        self,
        owner: str,
        game_id: str,
        plugin_name: str,
        run_fn: Callable[[dict | None], Any],
        config: dict | None = None,
    ) -> str:
        """Submit a task for background execution.

        Args:
            owner: Client/session identifier for ownership.
            game_id: ID of the game being analyzed.
            plugin_name: Name of the analysis plugin.
            run_fn: Function to execute (takes config, returns result).
            config: Optional configuration for the plugin.

        Returns:
            Task ID for tracking.
        """
        task_id = str(uuid.uuid4())[:8]

        task = Task(
            id=task_id,
            owner=owner,
            status=TaskStatus.PENDING,
            plugin_name=plugin_name,
            game_id=game_id,
            config=config or {},
        )

        with self._lock:
            self._tasks[task_id] = task

        # Submit to thread pool
        self._executor.submit(self._run_task, task, run_fn)
        logger.info(f"Task {task_id} submitted: {plugin_name} on {game_id}")

        return task_id

    def _run_task(self, task: Task, run_fn: Callable[[dict | None], Any]) -> None:
        """Execute a task in a background thread."""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        logger.info(f"Task {task.id} started")

        try:
            # Check for early cancellation
            if task.cancel_event.is_set():
                task.completed_at = time.time()
                task.status = TaskStatus.CANCELLED
                logger.info(f"Task {task.id} cancelled before start")
                return

            # Inject cancel event into config so plugin can check it
            config_with_cancel = {**(task.config or {}), "_cancel_event": task.cancel_event}

            # Run the analysis
            result = run_fn(config_with_cancel)

            # Set completed_at BEFORE status to avoid race conditions
            task.completed_at = time.time()

            # Check if cancelled during execution
            if task.cancel_event.is_set():
                task.result = result  # May have partial results
                task.status = TaskStatus.CANCELLED
                logger.info(f"Task {task.id} cancelled during execution")
            else:
                task.result = result
                task.status = TaskStatus.COMPLETED
                logger.info(f"Task {task.id} completed")

        except Exception as e:
            task.completed_at = time.time()
            task.error = f"{type(e).__name__}: {e}"
            task.status = TaskStatus.FAILED
            logger.error(f"Task {task.id} failed: {e}")

    def get(self, task_id: str) -> Task | None:
        """Get a task by ID.

        Args:
            task_id: The task identifier.

        Returns:
            Task object or None if not found.
        """
        with self._lock:
            return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> bool:
        """Request cancellation of a task.

        Args:
            task_id: The task identifier.

        Returns:
            True if cancellation was requested, False if task not found.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False

            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return False  # Already finished

            task.cancel_event.set()
            logger.info(f"Task {task_id} cancellation requested")
            return True

    def list_tasks(self, owner: str | None = None) -> list[Task]:
        """List tasks, optionally filtered by owner.

        Args:
            owner: Filter to tasks owned by this client (None for all).

        Returns:
            List of tasks.
        """
        with self._lock:
            tasks = list(self._tasks.values())
            if owner is not None:
                tasks = [t for t in tasks if t.owner == owner]
            return tasks

    def cleanup(self, max_age_seconds: int = 3600) -> int:
        """Remove completed tasks older than threshold.

        Args:
            max_age_seconds: Maximum age of completed tasks to keep.

        Returns:
            Number of tasks removed.
        """
        now = time.time()
        removed = 0

        with self._lock:
            to_remove = []
            for task_id, task in self._tasks.items():
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    if task.completed_at and (now - task.completed_at) > max_age_seconds:
                        to_remove.append(task_id)

            for task_id in to_remove:
                del self._tasks[task_id]
                removed += 1

        if removed:
            logger.info(f"Cleaned up {removed} old tasks")
        return removed

    def shutdown(self) -> None:
        """Shutdown the executor gracefully."""
        self._executor.shutdown(wait=False)


# Global task manager instance
task_manager = TaskManager()
