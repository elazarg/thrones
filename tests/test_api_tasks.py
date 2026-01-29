"""Tests for the Task API endpoints."""
import time
import typing

import pytest
from fastapi.testclient import TestClient

from app.core.tasks import TaskStatus
from app.dependencies import get_task_manager
from app.main import app


@pytest.fixture
def client() -> typing.Iterator[TestClient]:
    """Return FastAPI test client with proper lifespan handling."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def isolate_task_manager():
    """
    Ensure no background threads leak across tests.

    Key idea: do *all* shutdown/waiting in fixture teardown (after the test body
    but before pytest closes its capture streams), so background logs can't write
    to a closed stream.
    """
    yield

    tasks = get_task_manager()

    # 1) Request cancellation for anything not finished
    for t in tasks.list_tasks():
        if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            tasks.cancel(t.id)

    # 2) Stop the executor and wait for worker threads to exit.
    #    Use wait=False to avoid blocking forever if a task is stuck.
    #    The cancel_futures=True will prevent new tasks from starting.
    tasks.shutdown(wait=False, cancel_futures=True)

    # 3) Remove tasks created during this test
    tasks.cleanup(max_age_seconds=0)


class TestSubmitTask:
    def test_submit_task_success(self, client: TestClient):
        response = client.post(
            "/api/tasks",
            params={"game_id": "trust-game", "plugin": "Validation", "owner": "test-user"},
        )
        assert response.status_code == 200
        data = response.json()
        # Now returns full task object with 'id' instead of 'task_id'
        assert "id" in data
        assert data["status"] in ("pending", "running", "completed")
        assert data["plugin_name"] == "Validation"
        assert data["game_id"] == "trust-game"
        assert data["owner"] == "test-user"

    def test_submit_task_unknown_game(self, client: TestClient):
        response = client.post("/api/tasks", params={"game_id": "nonexistent", "plugin": "Validation"})
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]

    def test_submit_task_unknown_plugin(self, client: TestClient):
        response = client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "NonexistentPlugin"})
        assert response.status_code == 400
        assert "Unknown plugin" in response.json()["detail"]

    def test_submit_task_with_config(self, client: TestClient):
        response = client.post(
            "/api/tasks",
            params={"game_id": "trust-game", "plugin": "Validation", "solver": "quick", "max_equilibria": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["config"] == {"solver": "quick", "max_equilibria": 5}


class TestGetTask:
    def test_get_task_pending(self, client: TestClient):
        submit_resp = client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "Validation"})
        task_id = submit_resp.json()["id"]

        response = client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["plugin_name"] == "Validation"
        assert data["game_id"] == "trust-game"
        assert data["status"] in ("pending", "running", "completed")

    def test_get_task_completed(self, client: TestClient):
        submit_resp = client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "Validation"})
        task_id = submit_resp.json()["id"]

        # Wait for completion (5 seconds max)
        status = None
        for _ in range(100):
            response = client.get(f"/api/tasks/{task_id}")
            status = response.json()["status"]
            if status == "completed":
                break
            time.sleep(0.05)

        assert status == "completed", f"Task did not complete in time, status: {status}"
        data = response.json()
        assert data["result"] is not None
        assert "summary" in data["result"]
        assert data["completed_at"] is not None

    def test_get_task_not_found(self, client: TestClient):
        response = client.get("/api/tasks/nonexistent")
        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]


class TestCancelTask:
    def test_cancel_task_not_found(self, client: TestClient):
        response = client.delete("/api/tasks/nonexistent")
        assert response.status_code == 404

    def test_cancel_completed_task(self, client: TestClient):
        submit_resp = client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "Validation"})
        task_id = submit_resp.json()["id"]

        # Wait for completion (5 seconds max)
        status = None
        for _ in range(100):
            get_resp = client.get(f"/api/tasks/{task_id}")
            status = get_resp.json()["status"]
            if status == "completed":
                break
            time.sleep(0.05)
        assert status == "completed", f"Task did not complete in time, status: {status}"

        response = client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["cancelled"] is False
        assert "already" in data["reason"]
        # Now includes full task state
        assert "task" in data
        assert data["task"]["id"] == task_id

    def test_cancel_returns_task_state(self, client: TestClient):
        """Verify that successful cancellation returns the task state."""
        submit_resp = client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "Validation"})
        task_id = submit_resp.json()["id"]

        # Cancel immediately (may or may not succeed depending on timing)
        response = client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert "cancelled" in data
        assert "task" in data
        assert data["task"]["id"] == task_id


class TestListTasks:
    def test_list_all_tasks(self, client: TestClient):
        client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "Validation", "owner": "user1"})
        client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "Validation", "owner": "user2"})

        response = client.get("/api/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_list_tasks_by_owner(self, client: TestClient):
        client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "Validation", "owner": "alice"})
        client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "Validation", "owner": "bob"})

        response = client.get("/api/tasks", params={"owner": "alice"})
        assert response.status_code == 200
        data = response.json()
        assert all(t["owner"] == "alice" for t in data)


class TestTaskIntegration:
    def test_full_workflow(self, client: TestClient):
        submit_resp = client.post(
            "/api/tasks",
            params={"game_id": "trust-game", "plugin": "Validation", "owner": "integration-test"},
        )
        assert submit_resp.status_code == 200
        task_id = submit_resp.json()["id"]

        result = None
        status = None
        for _ in range(100):
            poll_resp = client.get(f"/api/tasks/{task_id}")
            assert poll_resp.status_code == 200
            task_data = poll_resp.json()
            status = task_data["status"]

            if status == "completed":
                result = task_data["result"]
                break
            if status == "failed":
                pytest.fail(f"Task failed: {task_data['error']}")

            time.sleep(0.05)

        assert status == "completed", f"Task did not complete in time, status: {status}"
        assert result is not None
        assert "summary" in result
        assert "details" in result
