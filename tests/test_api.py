"""Tests for FastAPI endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient


class TestGameEndpoint:
    def test_get_game(self, client: TestClient):
        response = client.get("/api/game")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "trust-game"
        assert data["title"] == "Trust Game"
        assert data["players"] == ["Alice", "Bob"]
        assert "n_start" in data["nodes"]
        assert "o_coop" in data["outcomes"]

    def test_game_structure(self, client: TestClient):
        response = client.get("/api/game")
        data = response.json()
        # Check node structure
        start_node = data["nodes"]["n_start"]
        assert start_node["player"] == "Alice"
        assert len(start_node["actions"]) == 2
        # Check outcome structure
        coop_outcome = data["outcomes"]["o_coop"]
        assert coop_outcome["label"] == "Cooperate"
        assert coop_outcome["payoffs"] == {"Alice": 1, "Bob": 1}


class TestAnalysesEndpoint:
    def test_get_analyses(self, client: TestClient):
        response = client.get("/api/analyses")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least Nash analysis

    def test_nash_analysis_result(self, client: TestClient):
        response = client.get("/api/analyses")
        data = response.json()
        # Find Nash result
        nash_result = next(
            (r for r in data if "Nash" in r["summary"]),
            None,
        )
        assert nash_result is not None
        assert "equilibria" in nash_result["details"]
        equilibria = nash_result["details"]["equilibria"]
        assert len(equilibria) >= 1

    def test_equilibrium_has_required_fields(self, client: TestClient):
        response = client.get("/api/analyses")
        data = response.json()
        nash_result = next(r for r in data if "Nash" in r["summary"])
        eq = nash_result["details"]["equilibria"][0]
        # Check new fields exist (from API mismatch fix)
        assert "description" in eq
        assert "behavior_profile" in eq
        assert "outcomes" in eq
        # Check legacy fields also exist
        assert "strategies" in eq
        assert "payoffs" in eq
