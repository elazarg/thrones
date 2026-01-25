"""Tests for the Task API endpoints."""
import time

import pytest
from fastapi.testclient import TestClient

from app.core.tasks import task_manager
from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Return FastAPI test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_tasks():
    """Clean up tasks after each test."""
    yield
    # Remove all tasks
    task_manager.cleanup(max_age_seconds=0)


class TestSubmitTask:
    def test_submit_task_success(self, client: TestClient):
        """Should submit a task and return task_id."""
        response = client.post(
            "/api/tasks",
            params={
                "game_id": "trust-game",
                "plugin": "Nash Equilibrium",
                "owner": "test-user",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        assert data["plugin"] == "Nash Equilibrium"
        assert data["game_id"] == "trust-game"

    def test_submit_task_unknown_game(self, client: TestClient):
        """Should return 404 for unknown game."""
        response = client.post(
            "/api/tasks",
            params={
                "game_id": "nonexistent",
                "plugin": "Nash Equilibrium",
            },
        )
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]

    def test_submit_task_unknown_plugin(self, client: TestClient):
        """Should return 400 for unknown plugin."""
        response = client.post(
            "/api/tasks",
            params={
                "game_id": "trust-game",
                "plugin": "NonexistentPlugin",
            },
        )
        assert response.status_code == 400
        assert "Unknown plugin" in response.json()["detail"]

    def test_submit_task_with_config(self, client: TestClient):
        """Should accept solver configuration."""
        response = client.post(
            "/api/tasks",
            params={
                "game_id": "trust-game",
                "plugin": "Nash Equilibrium",
                "solver": "quick",
                "max_equilibria": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data


class TestGetTask:
    def test_get_task_pending(self, client: TestClient):
        """Should return task in pending/running state."""
        # Submit a task
        submit_resp = client.post(
            "/api/tasks",
            params={
                "game_id": "trust-game",
                "plugin": "Nash Equilibrium",
            },
        )
        task_id = submit_resp.json()["task_id"]

        # Get the task
        response = client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["plugin_name"] == "Nash Equilibrium"
        assert data["game_id"] == "trust-game"
        assert data["status"] in ("pending", "running", "completed")

    def test_get_task_completed(self, client: TestClient):
        """Should return completed task with result."""
        # Submit a task
        submit_resp = client.post(
            "/api/tasks",
            params={
                "game_id": "trust-game",
                "plugin": "Nash Equilibrium",
            },
        )
        task_id = submit_resp.json()["task_id"]

        # Wait for completion
        for _ in range(100):
            response = client.get(f"/api/tasks/{task_id}")
            if response.json()["status"] == "completed":
                break
            time.sleep(0.05)

        data = response.json()
        assert data["status"] == "completed"
        assert data["result"] is not None
        assert "summary" in data["result"]
        assert data["completed_at"] is not None

    def test_get_task_not_found(self, client: TestClient):
        """Should return 404 for unknown task."""
        response = client.get("/api/tasks/nonexistent")
        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]


class TestCancelTask:
    def test_cancel_task_not_found(self, client: TestClient):
        """Should return 404 for unknown task."""
        response = client.delete("/api/tasks/nonexistent")
        assert response.status_code == 404

    def test_cancel_completed_task(self, client: TestClient):
        """Should indicate task already completed."""
        # Submit and wait for completion
        submit_resp = client.post(
            "/api/tasks",
            params={
                "game_id": "trust-game",
                "plugin": "Nash Equilibrium",
            },
        )
        task_id = submit_resp.json()["task_id"]

        # Wait for completion
        for _ in range(100):
            get_resp = client.get(f"/api/tasks/{task_id}")
            if get_resp.json()["status"] == "completed":
                break
            time.sleep(0.05)

        # Try to cancel
        response = client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["cancelled"] is False
        assert "already" in data["reason"]


class TestListTasks:
    def test_list_all_tasks(self, client: TestClient):
        """Should list all submitted tasks."""
        # Submit a couple of tasks
        client.post(
            "/api/tasks",
            params={"game_id": "trust-game", "plugin": "Nash Equilibrium", "owner": "user1"},
        )
        client.post(
            "/api/tasks",
            params={"game_id": "trust-game", "plugin": "Validation", "owner": "user2"},
        )

        # List all
        response = client.get("/api/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_list_tasks_by_owner(self, client: TestClient):
        """Should filter tasks by owner."""
        # Submit tasks for different owners
        client.post(
            "/api/tasks",
            params={"game_id": "trust-game", "plugin": "Nash Equilibrium", "owner": "alice"},
        )
        client.post(
            "/api/tasks",
            params={"game_id": "trust-game", "plugin": "Nash Equilibrium", "owner": "bob"},
        )

        # List Alice's tasks
        response = client.get("/api/tasks", params={"owner": "alice"})
        assert response.status_code == 200
        data = response.json()
        assert all(t["owner"] == "alice" for t in data)


class TestTaskIntegration:
    def test_full_workflow(self, client: TestClient):
        """Test complete workflow: submit -> poll -> get result."""
        # 1. Submit task
        submit_resp = client.post(
            "/api/tasks",
            params={
                "game_id": "trust-game",
                "plugin": "Nash Equilibrium",
                "owner": "integration-test",
            },
        )
        assert submit_resp.status_code == 200
        task_id = submit_resp.json()["task_id"]

        # 2. Poll until complete
        result = None
        for _ in range(100):
            poll_resp = client.get(f"/api/tasks/{task_id}")
            assert poll_resp.status_code == 200
            task_data = poll_resp.json()

            if task_data["status"] == "completed":
                result = task_data["result"]
                break
            elif task_data["status"] == "failed":
                pytest.fail(f"Task failed: {task_data['error']}")

            time.sleep(0.05)

        # 3. Verify result
        assert result is not None
        assert "summary" in result
        assert "details" in result
        assert "equilibria" in result["details"]
