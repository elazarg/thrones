"""Integration tests: main app + plugins.

These tests verify the full flow from the main app through remote plugins.
They require plugin venvs to be set up (scripts/setup-plugins.ps1).
"""
from __future__ import annotations

import io
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.plugins import plugin_manager


@pytest.fixture(scope="module")
def client():
    """Create a test client with lifespan events (starts plugins)."""
    with TestClient(app) as c:
        yield c


def _gambit_available(client) -> bool:
    """Check if the gambit plugin is healthy."""
    for pp in plugin_manager.healthy_plugins():
        if pp.config.name == "gambit":
            return True
    return False


def _vegas_available(client) -> bool:
    """Check if the vegas plugin is healthy."""
    for pp in plugin_manager.healthy_plugins():
        if pp.config.name == "vegas":
            return True
    return False


# ---------------------------------------------------------------------------
# Format parsing via plugin
# ---------------------------------------------------------------------------


class TestEFGUpload:
    """Test uploading .efg files (requires gambit plugin for parsing)."""

    EFG_CONTENT = (
        'EFG 2 R "Test Game" { "P1" "P2" }\n'
        'p "" 1 1 "" { "L" "R" } 0\n'
        't "" 1 "Left" { 1, 0 }\n'
        't "" 2 "Right" { 0, 1 }\n'
    )

    def test_efg_upload(self, client):
        if not _gambit_available(client):
            pytest.skip("Gambit plugin not running")

        resp = client.post(
            "/api/games/upload",
            files={"file": ("test.efg", io.BytesIO(self.EFG_CONTENT.encode()), "text/plain")},
        )
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        data = resp.json()
        assert data["title"] == "Test Game"
        assert data["format_name"] == "extensive"
        assert "P1" in data["players"]
        assert "P2" in data["players"]

    def test_efg_upload_trust_game(self, client):
        if not _gambit_available(client):
            pytest.skip("Gambit plugin not running")

        efg = (
            'EFG 2 R "Trust Game" { "Alice" "Bob" }\n'
            'p "" 1 1 "" { "Trust" "Don\'t" } 0\n'
            'p "" 2 1 "" { "Honor" "Betray" } 0\n'
            't "" 1 "Cooperate" { 1, 1 }\n'
            't "" 2 "Betray" { -1, 2 }\n'
            't "" 3 "Decline" { 0, 0 }\n'
        )
        resp = client.post(
            "/api/games/upload",
            files={"file": ("trust.efg", io.BytesIO(efg.encode()), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Trust Game"
        assert "Alice" in data["players"]
        assert "Bob" in data["players"]


class TestNFGUpload:
    """Test uploading .nfg files (requires gambit plugin for parsing)."""

    NFG_CONTENT = (
        'NFG 1 R "PD" { "Row" "Col" }\n'
        '{ { "C" "D" } { "C" "D" } }\n'
        '\n'
        '3 3 0 5 5 0 1 1\n'
    )

    def test_nfg_upload(self, client):
        if not _gambit_available(client):
            pytest.skip("Gambit plugin not running")

        resp = client.post(
            "/api/games/upload",
            files={"file": ("pd.nfg", io.BytesIO(self.NFG_CONTENT.encode()), "text/plain")},
        )
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        data = resp.json()
        assert data["title"] == "PD"
        assert data["format_name"] == "normal"
        assert "Row" in data["players"]
        assert "Col" in data["players"]


# ---------------------------------------------------------------------------
# Analysis via plugin
# ---------------------------------------------------------------------------


class TestAnalysisFlow:
    """Test analysis via remote plugin."""

    def _upload_json_game(self, client) -> str:
        """Upload a JSON game and return its ID."""
        import json

        game = {
            "id": "integration-test-game",
            "title": "Integration Test Game",
            "players": ["Alice", "Bob"],
            "tags": [],
            "game_efg": {
                "root": "n_start",
                "nodes": {
                    "n_start": {
                        "id": "n_start",
                        "player": "Alice",
                        "actions": [
                            {"label": "Trust", "target": "n_bob"},
                            {"label": "Don't", "target": "o_decline"},
                        ],
                    },
                    "n_bob": {
                        "id": "n_bob",
                        "player": "Bob",
                        "actions": [
                            {"label": "Honor", "target": "o_coop"},
                            {"label": "Betray", "target": "o_betray"},
                        ],
                    },
                },
                "outcomes": {
                    "o_coop": {"label": "Cooperate", "payoffs": {"Alice": 1, "Bob": 1}},
                    "o_betray": {"label": "Betray", "payoffs": {"Alice": -1, "Bob": 2}},
                    "o_decline": {"label": "Decline", "payoffs": {"Alice": 0, "Bob": 0}},
                },
            },
        }
        content = json.dumps(game)
        resp = client.post(
            "/api/games/upload",
            files={"file": ("test.json", io.BytesIO(content.encode()), "application/json")},
        )
        assert resp.status_code == 200
        return resp.json()["id"]

    def test_analyses_include_remote_plugins(self, client):
        """When gambit plugin is running, analyses should include its results."""
        if not _gambit_available(client):
            pytest.skip("Gambit plugin not running")

        game_id = self._upload_json_game(client)

        resp = client.get(f"/api/games/{game_id}/analyses")
        assert resp.status_code == 200
        results = resp.json()

        # Should have results from remote analyses (Nash, IESDS)
        summaries = [r["summary"] for r in results]
        has_nash = any("Nash" in s or "equilibri" in s for s in summaries)
        assert has_nash, f"Expected Nash analysis in results, got: {summaries}"

    def test_task_api_with_remote_plugin(self, client):
        """Submit a task to a remote plugin via the task API."""
        if not _gambit_available(client):
            pytest.skip("Gambit plugin not running")

        game_id = self._upload_json_game(client)

        # Submit Nash analysis task
        resp = client.post(
            "/api/tasks",
            params={
                "game_id": game_id,
                "plugin": "Nash Equilibrium",
                "solver": "exhaustive",
            },
        )
        assert resp.status_code == 200, f"Task submission failed: {resp.text}"
        task_data = resp.json()
        task_id = task_data["task_id"]
        assert task_id

        # Poll for completion
        for _ in range(30):
            resp = client.get(f"/api/tasks/{task_id}")
            assert resp.status_code == 200
            status = resp.json()["status"]
            if status in ("completed", "failed"):
                break
            time.sleep(0.2)

        assert status == "completed", f"Task ended with status: {status}"
        result = resp.json()["result"]
        assert "equilibri" in result["summary"].lower() or "Nash" in result["summary"]


# ---------------------------------------------------------------------------
# Plugin health checks
# ---------------------------------------------------------------------------


class TestPluginHealth:
    """Verify plugin processes are healthy after startup."""

    def test_at_least_one_healthy_plugin(self, client):
        """At least one plugin should be healthy after app startup."""
        healthy = plugin_manager.healthy_plugins()
        # This may skip in CI environments without plugin venvs
        if not healthy:
            pytest.skip("No plugins healthy (plugin venvs may not be set up)")
        assert len(healthy) >= 1

    def test_gambit_plugin_info_has_formats(self, client):
        """Gambit plugin should advertise format support."""
        if not _gambit_available(client):
            pytest.skip("Gambit plugin not running")

        for pp in plugin_manager.healthy_plugins():
            if pp.config.name == "gambit":
                assert ".efg" in pp.info.get("formats", [])
                assert ".nfg" in pp.info.get("formats", [])
                return
        pytest.fail("Gambit plugin not found")

    def test_supported_formats_include_efg_nfg(self, client):
        """When gambit plugin is running, .efg and .nfg should be supported formats."""
        if not _gambit_available(client):
            pytest.skip("Gambit plugin not running")

        from app.formats import supported_formats

        formats = supported_formats()
        assert ".efg" in formats
        assert ".nfg" in formats


# ---------------------------------------------------------------------------
# Vegas plugin tests
# ---------------------------------------------------------------------------


class TestVegasUpload:
    """Test uploading .vg files (requires vegas plugin for parsing)."""

    PRISONERS_VG = '''
game main() {
  join A() $ 100;
  join B() $ 100;
  yield or split A(c: bool) B(c: bool);
  withdraw
    (A.c && B.c )   ? { A -> 100; B -> 100 }
  : (A.c && !B.c) ? { A -> 0; B -> 200 }
  : (!A.c && B.c) ? { A -> 200; B -> 0 }
  :                 { A -> 90; B -> 110 }
}
'''

    def test_vg_upload(self, client):
        """Test uploading a .vg file produces a MAID game."""
        if not _vegas_available(client):
            pytest.skip("Vegas plugin not running")

        resp = client.post(
            "/api/games/upload",
            files={"file": ("prisoners.vg", io.BytesIO(self.PRISONERS_VG.encode()), "text/plain")},
        )
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        data = resp.json()
        assert data["format_name"] == "maid"
        assert "A" in data["agents"]
        assert "B" in data["agents"]

    def test_vegas_plugin_info_has_formats(self, client):
        """Vegas plugin should advertise .vg format support."""
        if not _vegas_available(client):
            pytest.skip("Vegas plugin not running")

        for pp in plugin_manager.healthy_plugins():
            if pp.config.name == "vegas":
                assert ".vg" in pp.info.get("formats", [])
                return
        pytest.fail("Vegas plugin not found")

    def test_supported_formats_include_vg(self, client):
        """When vegas plugin is running, .vg should be a supported format."""
        if not _vegas_available(client):
            pytest.skip("Vegas plugin not running")

        from app.formats import supported_formats

        formats = supported_formats()
        assert ".vg" in formats
