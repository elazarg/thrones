"""Tests for the task management system."""
import time

import typing
import pytest

from app.core.tasks import Task, TaskManager, TaskStatus


@pytest.fixture
def manager() -> typing.Iterator[TaskManager]:
    """Create a fresh TaskManager for each test."""
    mgr = TaskManager(max_workers=2)
    yield mgr
    mgr.shutdown()


class TestTaskStatus:
    def test_status_values(self):
        """Status enum should have expected values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.FAILED.value == "failed"


class TestTask:
    def test_task_creation(self):
        """Task should be created with default values."""
        task = Task(
            id="test-1",
            owner="user-1",
            status=TaskStatus.PENDING,
            plugin_name="Nash",
            game_id="game-1",
        )
        assert task.id == "test-1"
        assert task.owner == "user-1"
        assert task.status == TaskStatus.PENDING
        assert task.result is None
        assert task.error is None
        assert not task.cancel_event.is_set()

    def test_task_to_dict(self):
        """Task should serialize to dictionary."""
        task = Task(
            id="test-1",
            owner="user-1",
            status=TaskStatus.COMPLETED,
            plugin_name="Nash",
            game_id="game-1",
            result={"equilibria": []},
        )
        d = task.to_dict()
        assert d["id"] == "test-1"
        assert d["status"] == "completed"
        assert d["result"] == {"equilibria": []}


class TestTaskManager:
    def test_submit_returns_task_id(self, manager: TaskManager):
        """Submit should return a task ID."""

        def dummy_fn(config):
            return {"result": "done"}

        task_id = manager.submit(
            owner="user-1",
            game_id="game-1",
            plugin_name="Test",
            run_fn=dummy_fn,
        )
        assert task_id is not None
        assert len(task_id) == 8  # Short UUID

    def test_get_task(self, manager: TaskManager):
        """Should retrieve submitted task."""

        def dummy_fn(config):
            time.sleep(0.1)
            return {"result": "done"}

        task_id = manager.submit(
            owner="user-1",
            game_id="game-1",
            plugin_name="Test",
            run_fn=dummy_fn,
        )

        task = manager.get(task_id)
        assert task is not None
        assert task.id == task_id
        assert task.owner == "user-1"
        assert task.game_id == "game-1"
        assert task.plugin_name == "Test"

    def test_get_nonexistent_task(self, manager: TaskManager):
        """Should return None for unknown task."""
        task = manager.get("nonexistent")
        assert task is None

    def test_task_completes(self, manager: TaskManager):
        """Task should complete and store result."""

        def compute_fn(config):
            return {"answer": 42}

        task_id = manager.submit(
            owner="user-1",
            game_id="game-1",
            plugin_name="Test",
            run_fn=compute_fn,
        )

        # Wait for completion (2.5 seconds max)
        status = None
        for _ in range(50):
            task = manager.get(task_id)
            if task:
                status = task.status
                if status == TaskStatus.COMPLETED:
                    break
            time.sleep(0.05)

        assert status == TaskStatus.COMPLETED, f"Task did not complete in time, status: {status}"
        task = manager.get(task_id)
        assert task is not None
        assert task.result == {"answer": 42}
        assert task.error is None
        assert task.completed_at is not None

    def test_task_failure(self, manager: TaskManager):
        """Failed task should store error."""

        def failing_fn(config):
            raise ValueError("Something went wrong")

        task_id = manager.submit(
            owner="user-1",
            game_id="game-1",
            plugin_name="Test",
            run_fn=failing_fn,
        )

        # Wait for failure (2.5 seconds max)
        status = None
        for _ in range(50):
            task = manager.get(task_id)
            if task:
                status = task.status
                if status == TaskStatus.FAILED:
                    break
            time.sleep(0.05)

        assert status == TaskStatus.FAILED, f"Task did not fail in time, status: {status}"
        task = manager.get(task_id)
        assert task is not None
        assert "ValueError" in task.error
        assert "Something went wrong" in task.error

    def test_task_cancellation(self, manager: TaskManager):
        """Task should be cancellable."""

        def long_running_fn(config):
            cancel_event = config.get("_cancel_event")
            for _ in range(100):
                if cancel_event and cancel_event.is_set():
                    return {"partial": True}
                time.sleep(0.05)
            return {"complete": True}

        task_id = manager.submit(
            owner="user-1",
            game_id="game-1",
            plugin_name="Test",
            run_fn=long_running_fn,
        )

        # Wait a bit then cancel
        time.sleep(0.1)
        result = manager.cancel(task_id)
        assert result is True

        # Wait for task to notice cancellation (2.5 seconds max)
        status = None
        for _ in range(50):
            task = manager.get(task_id)
            if task:
                status = task.status
                if status == TaskStatus.CANCELLED:
                    break
            time.sleep(0.05)

        assert status == TaskStatus.CANCELLED, f"Task was not cancelled in time, status: {status}"

    def test_cancel_nonexistent_task(self, manager: TaskManager):
        """Cancel should return False for unknown task."""
        result = manager.cancel("nonexistent")
        assert result is False

    def test_cancel_completed_task(self, manager: TaskManager):
        """Cancel should return False for already completed task."""

        def quick_fn(config):
            return {"done": True}

        task_id = manager.submit(
            owner="user-1",
            game_id="game-1",
            plugin_name="Test",
            run_fn=quick_fn,
        )

        # Wait for completion
        for _ in range(50):
            task = manager.get(task_id)
            if task and task.status == TaskStatus.COMPLETED:
                break
            time.sleep(0.05)

        result = manager.cancel(task_id)
        assert result is False

    def test_list_tasks_all(self, manager: TaskManager):
        """Should list all tasks."""

        def dummy_fn(config):
            time.sleep(0.2)
            return {}

        manager.submit(owner="user-1", game_id="game-1", plugin_name="Test", run_fn=dummy_fn)
        manager.submit(owner="user-2", game_id="game-2", plugin_name="Test", run_fn=dummy_fn)

        tasks = manager.list_tasks()
        assert len(tasks) == 2

    def test_list_tasks_by_owner(self, manager: TaskManager):
        """Should filter tasks by owner."""

        def dummy_fn(config):
            time.sleep(0.2)
            return {}

        manager.submit(owner="user-1", game_id="game-1", plugin_name="Test", run_fn=dummy_fn)
        manager.submit(owner="user-1", game_id="game-2", plugin_name="Test", run_fn=dummy_fn)
        manager.submit(owner="user-2", game_id="game-3", plugin_name="Test", run_fn=dummy_fn)

        tasks = manager.list_tasks(owner="user-1")
        assert len(tasks) == 2
        assert all(t.owner == "user-1" for t in tasks)

    def test_config_passed_to_function(self, manager: TaskManager):
        """Config should be passed to the run function."""
        received_config = {}

        def capture_config(config):
            received_config.update(config)
            return {"captured": True}

        manager.submit(
            owner="user-1",
            game_id="game-1",
            plugin_name="Test",
            run_fn=capture_config,
            config={"solver": "quick", "max_equilibria": 5},
        )

        # Wait for completion
        time.sleep(0.2)

        assert received_config.get("solver") == "quick"
        assert received_config.get("max_equilibria") == 5
        assert "_cancel_event" in received_config  # Injected by manager

    def test_cleanup_old_tasks(self, manager: TaskManager):
        """Should remove old completed tasks."""

        def quick_fn(config):
            return {}

        task_id = manager.submit(
            owner="user-1",
            game_id="game-1",
            plugin_name="Test",
            run_fn=quick_fn,
        )

        # Wait for completion
        for _ in range(50):
            task = manager.get(task_id)
            if task and task.status == TaskStatus.COMPLETED:
                break
            time.sleep(0.05)

        # Wait a bit more to ensure the task is "old" enough
        time.sleep(0.1)

        # Cleanup with very short max age (0.05 seconds)
        removed = manager.cleanup(max_age_seconds=0)
        assert removed == 1

        # Task should be gone
        assert manager.get(task_id) is None

    def test_cleanup_preserves_running_tasks(self, manager: TaskManager):
        """Should not remove running tasks."""

        def long_fn(config):
            time.sleep(1)
            return {}

        task_id = manager.submit(
            owner="user-1",
            game_id="game-1",
            plugin_name="Test",
            run_fn=long_fn,
        )

        time.sleep(0.1)  # Let it start

        # Cleanup with zero age - should not remove running task
        removed = manager.cleanup(max_age_seconds=0)
        assert removed == 0

        # Task should still exist
        assert manager.get(task_id) is not None

        # Cancel to clean up
        manager.cancel(task_id)
