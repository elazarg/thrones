"""Tests for the Task API endpoints."""
import time
import typing

import pytest
from fastapi.testclient import TestClient

from app.core.tasks import task_manager, TaskStatus
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

    # 1) Request cancellation for anything not finished
    for t in task_manager.list_tasks():
        if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            task_manager.cancel(t.id)

    # 2) Stop the executor and wait for worker threads to exit.
    #    With the restartable TaskManager you implemented, the next test can submit again.
    task_manager.shutdown(wait=True, cancel_futures=True)

    # 3) Remove tasks created during this test
    task_manager.cleanup(max_age_seconds=0)


class TestSubmitTask:
    def test_submit_task_success(self, client: TestClient):
        response = client.post(
            "/api/tasks",
            params={"game_id": "trust-game", "plugin": "Nash Equilibrium", "owner": "test-user"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        assert data["plugin"] == "Nash Equilibrium"
        assert data["game_id"] == "trust-game"

    def test_submit_task_unknown_game(self, client: TestClient):
        response = client.post("/api/tasks", params={"game_id": "nonexistent", "plugin": "Nash Equilibrium"})
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]

    def test_submit_task_unknown_plugin(self, client: TestClient):
        response = client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "NonexistentPlugin"})
        assert response.status_code == 400
        assert "Unknown plugin" in response.json()["detail"]

    def test_submit_task_with_config(self, client: TestClient):
        response = client.post(
            "/api/tasks",
            params={"game_id": "trust-game", "plugin": "Nash Equilibrium", "solver": "quick", "max_equilibria": 5},
        )
        assert response.status_code == 200
        assert "task_id" in response.json()


class TestGetTask:
    def test_get_task_pending(self, client: TestClient):
        submit_resp = client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "Nash Equilibrium"})
        task_id = submit_resp.json()["task_id"]

        response = client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["plugin_name"] == "Nash Equilibrium"
        assert data["game_id"] == "trust-game"
        assert data["status"] in ("pending", "running", "completed")

    def test_get_task_completed(self, client: TestClient):
        submit_resp = client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "Nash Equilibrium"})
        task_id = submit_resp.json()["task_id"]

        # Wait for completion
        response = None
        for _ in range(100):
            response = client.get(f"/api/tasks/{task_id}")
            if response.json()["status"] == "completed":
                break
            time.sleep(0.05)

        assert response is not None
        data = response.json()
        assert data["status"] == "completed"
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
        submit_resp = client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "Nash Equilibrium"})
        task_id = submit_resp.json()["task_id"]

        # Wait for completion
        for _ in range(100):
            get_resp = client.get(f"/api/tasks/{task_id}")
            if get_resp.json()["status"] == "completed":
                break
            time.sleep(0.05)

        response = client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["cancelled"] is False
        assert "already" in data["reason"]


class TestListTasks:
    def test_list_all_tasks(self, client: TestClient):
        client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "Nash Equilibrium", "owner": "user1"})
        client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "Validation", "owner": "user2"})

        response = client.get("/api/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_list_tasks_by_owner(self, client: TestClient):
        client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "Nash Equilibrium", "owner": "alice"})
        client.post("/api/tasks", params={"game_id": "trust-game", "plugin": "Nash Equilibrium", "owner": "bob"})

        response = client.get("/api/tasks", params={"owner": "alice"})
        assert response.status_code == 200
        data = response.json()
        assert all(t["owner"] == "alice" for t in data)


class TestTaskIntegration:
    def test_full_workflow(self, client: TestClient):
        submit_resp = client.post(
            "/api/tasks",
            params={"game_id": "trust-game", "plugin": "Nash Equilibrium", "owner": "integration-test"},
        )
        assert submit_resp.status_code == 200
        task_id = submit_resp.json()["task_id"]

        result = None
        for _ in range(100):
            poll_resp = client.get(f"/api/tasks/{task_id}")
            assert poll_resp.status_code == 200
            task_data = poll_resp.json()

            if task_data["status"] == "completed":
                result = task_data["result"]
                break
            if task_data["status"] == "failed":
                pytest.fail(f"Task failed: {task_data['error']}")

            time.sleep(0.05)

        assert result is not None
        assert "summary" in result
        assert "details" in result
        assert "equilibria" in result["details"]
