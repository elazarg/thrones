"""Tests for FastAPI endpoints."""
from __future__ import annotations

import io

from fastapi.testclient import TestClient


class TestGamesListEndpoint:
    """Tests for /api/games endpoint."""

    def test_list_games(self, client: TestClient):
        response = client.get("/api/games")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least the Trust Game
        assert len(data) >= 1
        # Check summary format
        game = data[0]
        assert "id" in game
        assert "title" in game
        assert "players" in game

    def test_list_includes_trust_game(self, client: TestClient):
        response = client.get("/api/games")
        data = response.json()
        ids = [g["id"] for g in data]
        assert "trust-game" in ids


class TestGetGameEndpoint:
    """Tests for /api/games/{id} endpoint."""

    def test_get_game_by_id(self, client: TestClient):
        response = client.get("/api/games/trust-game")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "trust-game"
        assert data["title"] == "Trust Game"

    def test_get_nonexistent_game(self, client: TestClient):
        response = client.get("/api/games/not-a-real-game")
        assert response.status_code == 404


class TestUploadGameEndpoint:
    """Tests for /api/games/upload endpoint."""

    def test_upload_json_game(self, client: TestClient, clean_store):
        game_json = """{
            "id": "test-upload",
            "title": "Test Upload Game",
            "players": ["X", "Y"],
            "root": "n1",
            "nodes": {
                "n1": {
                    "id": "n1",
                    "player": "X",
                    "actions": [{"label": "A", "target": "o1"}]
                }
            },
            "outcomes": {
                "o1": {"label": "End", "payoffs": {"X": 1, "Y": 2}}
            },
            "version": "v1",
            "tags": []
        }"""
        files = {"file": ("test.json", io.BytesIO(game_json.encode()), "application/json")}
        response = client.post("/api/games/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Upload Game"

    def test_upload_invalid_format(self, client: TestClient):
        files = {"file": ("test.xyz", io.BytesIO(b"invalid"), "text/plain")}
        response = client.post("/api/games/upload", files=files)
        assert response.status_code == 400
        # Error is sanitized to not leak internal details
        assert "Invalid game format" in response.json()["detail"]

    def test_upload_malformed_json(self, client: TestClient):
        files = {"file": ("bad.json", io.BytesIO(b"not json"), "application/json")}
        response = client.post("/api/games/upload", files=files)
        # Parse error can be 400 or 500 depending on error type
        assert response.status_code in (400, 500)


class TestDeleteGameEndpoint:
    """Tests for DELETE /api/games/{id} endpoint."""

    def test_delete_game(self, client: TestClient, clean_store):
        # First upload a game
        game_json = """{
            "id": "to-delete",
            "title": "Delete Me",
            "players": ["A"],
            "root": "n1",
            "nodes": {"n1": {"id": "n1", "player": "A", "actions": [{"label": "X", "target": "o1"}]}},
            "outcomes": {"o1": {"label": "End", "payoffs": {"A": 0}}},
            "version": "v1",
            "tags": []
        }"""
        files = {"file": ("delete.json", io.BytesIO(game_json.encode()), "application/json")}
        response = client.post("/api/games/upload", files=files)
        game_id = response.json()["id"]

        # Now delete it
        response = client.delete(f"/api/games/{game_id}")
        assert response.status_code == 200

        # Verify it's gone
        response = client.get(f"/api/games/{game_id}")
        assert response.status_code == 404

    def test_delete_nonexistent_game(self, client: TestClient):
        response = client.delete("/api/games/not-real")
        assert response.status_code == 404


class TestGameAnalysesEndpoint:
    """Tests for /api/games/{id}/analyses endpoint."""

    def test_get_game_analyses(self, client: TestClient):
        response = client.get("/api/games/trust-game/analyses")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Check new structure with plugin attribution
        for item in data:
            assert "plugin_name" in item
            assert "result" in item
            assert "summary" in item["result"]
            assert "details" in item["result"]

    def test_analyses_for_nonexistent_game(self, client: TestClient):
        response = client.get("/api/games/fake-game/analyses")
        assert response.status_code == 404


class TestListAnalysesEndpoint:
    """Tests for /api/analyses endpoint."""

    def test_list_analyses(self, client: TestClient):
        response = client.get("/api/analyses")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Check structure
        for item in data:
            assert "name" in item
            assert "description" in item
            assert "applicable_to" in item
            assert "continuous" in item
