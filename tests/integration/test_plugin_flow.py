"""Integration tests: main app + plugins.

These tests verify the full flow from the main app through remote plugins.
They require plugin venvs to be set up (scripts/setup-plugins.ps1).
"""
from __future__ import annotations

import io
import time
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.plugins import plugin_manager, register_healthy_plugins


@pytest.fixture(scope="function")
def client():
    """Create a test client with lifespan events (starts plugins).

    Uses function scope to isolate tests - if one test hangs or fails,
    it won't block subsequent tests in the module.
    """
    with TestClient(app) as c:
        yield c


def _wait_for_plugin_discovery(timeout: float = 30.0) -> None:
    """Wait for background plugin discovery to complete."""
    deadline = time.monotonic() + timeout
    # Give the background thread a moment to start and set is_loading=True
    time.sleep(0.2)
    while plugin_manager.is_loading and time.monotonic() < deadline:
        time.sleep(0.1)


def _gambit_available(client) -> bool:
    """Check if the gambit plugin is healthy and registered."""
    # Wait for discovery to complete, then register formats
    _wait_for_plugin_discovery()
    register_healthy_plugins()
    for pp in plugin_manager.healthy_plugins():
        if pp.config.name == "gambit":
            return True
    return False


def _vegas_available(client) -> bool:
    """Check if the vegas plugin is healthy and registered."""
    # Wait for discovery to complete, then register formats
    _wait_for_plugin_discovery()
    register_healthy_plugins()
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

        # Results are PluginAnalysisResult: {"plugin_name": ..., "result": {"summary": ...}}
        summaries = [r["result"]["summary"] for r in results]
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
        task_id = task_data["id"]  # API returns 'id' not 'task_id'
        assert task_id

        # Poll for completion (10 seconds max - plugins can be slow)
        status = None
        for _ in range(50):
            resp = client.get(f"/api/tasks/{task_id}")
            assert resp.status_code == 200
            status = resp.json()["status"]
            if status in ("completed", "failed"):
                break
            time.sleep(0.2)

        assert status in ("completed", "failed"), f"Task did not finish in time, status: {status}"
        assert status == "completed", f"Task failed with status: {status}"
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
        """Test uploading a .vg file produces a VegasGame."""
        if not _vegas_available(client):
            pytest.skip("Vegas plugin not running")

        resp = client.post(
            "/api/games/upload",
            files={"file": ("prisoners.vg", io.BytesIO(self.PRISONERS_VG.encode()), "text/plain")},
        )
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        data = resp.json()
        assert data["format_name"] == "vegas"
        assert "A" in data["players"]
        assert "B" in data["players"]
        assert "source_code" in data

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

    def test_vg_to_maid_conversion(self, client):
        """Test conversion chain: Vegas → MAID."""
        if not _vegas_available(client):
            pytest.skip("Vegas plugin not running")

        # Upload .vg file
        resp = client.post(
            "/api/games/upload",
            files={"file": ("test.vg", io.BytesIO(self.PRISONERS_VG.encode()), "text/plain")},
        )
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        data = resp.json()
        game_id = data["id"]
        assert data["format_name"] == "vegas"

        # Request MAID conversion
        resp = client.get(f"/api/games/{game_id}/as/maid")
        assert resp.status_code == 200, f"MAID conversion failed: {resp.text}"
        maid = resp.json()
        assert maid["format_name"] == "maid"
        assert "agents" in maid
        assert "nodes" in maid

    @pytest.mark.slow
    def test_vg_to_efg_conversion(self, client):
        """Test full conversion chain: Vegas → MAID → EFG.

        This test requires both Vegas and PyCID plugins and can be slow
        due to PyCID library initialization.
        """
        if not _vegas_available(client):
            pytest.skip("Vegas plugin not running")

        # Also need PyCID for MAID→EFG conversion
        pycid_available = any(
            pp.config.name == "pycid" for pp in plugin_manager.healthy_plugins()
        )
        if not pycid_available:
            pytest.skip("PyCID plugin not running (needed for MAID→EFG)")

        # Upload .vg file
        resp = client.post(
            "/api/games/upload",
            files={"file": ("efg_test.vg", io.BytesIO(self.PRISONERS_VG.encode()), "text/plain")},
        )
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        data = resp.json()
        game_id = data["id"]
        assert data["format_name"] == "vegas"

        # Request EFG conversion (goes through MAID first)
        resp = client.get(f"/api/games/{game_id}/as/extensive")
        assert resp.status_code == 200, f"EFG conversion failed: {resp.text}"
        efg = resp.json()
        assert efg["format_name"] == "extensive"
        assert "root" in efg
        assert "nodes" in efg

    def test_vegas_plugin_info_has_compile_targets(self, client):
        """Vegas plugin should advertise compile_targets."""
        if not _vegas_available(client):
            pytest.skip("Vegas plugin not running")

        for pp in plugin_manager.healthy_plugins():
            if pp.config.name == "vegas":
                targets = pp.info.get("compile_targets", [])
                assert len(targets) >= 4, f"Expected at least 4 compile targets, got {targets}"
                target_ids = {t["id"] for t in targets}
                assert "solidity" in target_ids
                assert "vyper" in target_ids
                assert "smt" in target_ids
                assert "scribble" in target_ids
                return
        pytest.fail("Vegas plugin not found")


# ---------------------------------------------------------------------------
# EGTTools plugin tests
# ---------------------------------------------------------------------------


def _egttools_available(client) -> bool:
    """Check if the egttools plugin is healthy."""
    for pp in plugin_manager.healthy_plugins():
        if pp.config.name == "egttools":
            return True
    return False


class TestEGTToolsPlugin:
    """Test EGTTools plugin for evolutionary game theory analysis."""

    # Prisoner's Dilemma NFG for testing
    PD_NFG = (
        'NFG 1 R "Prisoner\'s Dilemma" { "Row" "Col" }\n'
        '{ { "Cooperate" "Defect" } { "Cooperate" "Defect" } }\n'
        '\n'
        '-1 -1 -3 0 0 -3 -2 -2\n'
    )

    def test_egttools_plugin_healthy(self, client):
        """Test that egttools plugin is running and healthy."""
        if not _egttools_available(client):
            pytest.skip("EGTTools plugin not running")

        for pp in plugin_manager.healthy_plugins():
            if pp.config.name == "egttools":
                assert pp.info.get("api_version") == 1
                return
        pytest.fail("EGTTools plugin not found")

    def test_egttools_advertises_analyses(self, client):
        """Test that egttools plugin advertises its analyses."""
        if not _egttools_available(client):
            pytest.skip("EGTTools plugin not running")

        for pp in plugin_manager.healthy_plugins():
            if pp.config.name == "egttools":
                analyses = pp.info.get("analyses", [])
                names = [a["name"] for a in analyses]
                assert "Replicator Dynamics" in names
                assert "Evolutionary Stability" in names
                return
        pytest.fail("EGTTools plugin not found")

    def _upload_nfg_game(self, client) -> str:
        """Upload an NFG game and return its ID."""
        if not _gambit_available(client):
            pytest.skip("Gambit plugin not running (needed for NFG parsing)")

        resp = client.post(
            "/api/games/upload",
            files={"file": ("pd.nfg", io.BytesIO(self.PD_NFG.encode()), "text/plain")},
        )
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        return resp.json()["id"]

    def test_replicator_dynamics_task(self, client):
        """Test running Replicator Dynamics analysis via task API."""
        if not _egttools_available(client):
            pytest.skip("EGTTools plugin not running")

        game_id = self._upload_nfg_game(client)

        # Submit Replicator Dynamics task
        resp = client.post(
            "/api/tasks",
            params={
                "game_id": game_id,
                "plugin": "Replicator Dynamics",
                "time_steps": 50,
            },
        )
        assert resp.status_code == 200, f"Task submission failed: {resp.text}"
        task_id = resp.json()["id"]

        # Poll for completion
        status = None
        for _ in range(30):
            resp = client.get(f"/api/tasks/{task_id}")
            assert resp.status_code == 200
            status = resp.json()["status"]
            if status in ("completed", "failed"):
                break
            time.sleep(0.1)

        assert status == "completed", f"Task did not complete: {status}"
        result = resp.json()["result"]
        assert "trajectory" in result.get("details", {})
        assert "final_state" in result.get("details", {})

    def test_evolutionary_stability_task(self, client):
        """Test running Evolutionary Stability analysis via task API."""
        if not _egttools_available(client):
            pytest.skip("EGTTools plugin not running")

        game_id = self._upload_nfg_game(client)

        # Submit Evolutionary Stability task
        resp = client.post(
            "/api/tasks",
            params={
                "game_id": game_id,
                "plugin": "Evolutionary Stability",
                "population_size": 50,
            },
        )
        assert resp.status_code == 200, f"Task submission failed: {resp.text}"
        task_id = resp.json()["id"]

        # Poll for completion
        status = None
        for _ in range(30):
            resp = client.get(f"/api/tasks/{task_id}")
            assert resp.status_code == 200
            status = resp.json()["status"]
            if status in ("completed", "failed"):
                break
            time.sleep(0.1)

        assert status == "completed", f"Task did not complete: {status}"
        result = resp.json()["result"]
        assert "stationary_distribution" in result.get("details", {})


# ---------------------------------------------------------------------------
# OpenSpiel plugin tests
# ---------------------------------------------------------------------------


def _openspiel_available(client) -> bool:
    """Check if the openspiel plugin is healthy."""
    for pp in plugin_manager.healthy_plugins():
        if pp.config.name == "openspiel":
            # Also check that it's not in error state (Windows)
            if pp.info.get("error"):
                return False
            return True
    return False


class TestOpenSpielPlugin:
    """Test OpenSpiel plugin for CFR and exploitability analysis.

    NOTE: OpenSpiel only works on Linux/macOS. These tests skip on Windows.
    """

    # Simple EFG for testing
    SIMPLE_EFG = (
        'EFG 2 R "Simple Game" { "P1" "P2" }\n'
        'p "" 1 1 "" { "L" "R" } 0\n'
        'p "" 2 1 "" { "l" "r" } 0\n'
        't "" 1 "Ll" { 3, 3 }\n'
        't "" 2 "Lr" { 0, 0 }\n'
        'p "" 2 1 "" { "l" "r" } 0\n'
        't "" 3 "Rl" { 0, 0 }\n'
        't "" 4 "Rr" { 1, 1 }\n'
    )

    def test_openspiel_plugin_healthy(self, client):
        """Test that openspiel plugin is running and healthy (non-Windows)."""
        if not _openspiel_available(client):
            pytest.skip("OpenSpiel plugin not running or not available on this platform")

        for pp in plugin_manager.healthy_plugins():
            if pp.config.name == "openspiel":
                assert pp.info.get("api_version") == 1
                return
        pytest.fail("OpenSpiel plugin not found")

    def test_openspiel_advertises_analyses(self, client):
        """Test that openspiel plugin advertises its analyses."""
        if not _openspiel_available(client):
            pytest.skip("OpenSpiel plugin not running or not available on this platform")

        for pp in plugin_manager.healthy_plugins():
            if pp.config.name == "openspiel":
                analyses = pp.info.get("analyses", [])
                names = [a["name"] for a in analyses]
                assert "CFR Equilibrium" in names
                assert "Exploitability" in names
                assert "CFR Convergence" in names
                return
        pytest.fail("OpenSpiel plugin not found")

    def _upload_efg_game(self, client) -> str:
        """Upload an EFG game and return its ID."""
        if not _gambit_available(client):
            pytest.skip("Gambit plugin not running (needed for EFG parsing)")

        resp = client.post(
            "/api/games/upload",
            files={"file": ("simple.efg", io.BytesIO(self.SIMPLE_EFG.encode()), "text/plain")},
        )
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        return resp.json()["id"]

    def test_cfr_equilibrium_task(self, client):
        """Test running CFR Equilibrium analysis via task API."""
        if not _openspiel_available(client):
            pytest.skip("OpenSpiel plugin not running or not available on this platform")

        game_id = self._upload_efg_game(client)

        # Submit CFR Equilibrium task
        resp = client.post(
            "/api/tasks",
            params={
                "game_id": game_id,
                "plugin": "CFR Equilibrium",
                "iterations": 100,
            },
        )
        assert resp.status_code == 200, f"Task submission failed: {resp.text}"
        task_id = resp.json()["id"]

        # Poll for completion
        status = None
        for _ in range(50):
            resp = client.get(f"/api/tasks/{task_id}")
            assert resp.status_code == 200
            status = resp.json()["status"]
            if status in ("completed", "failed"):
                break
            time.sleep(0.2)

        assert status == "completed", f"Task did not complete: {status}"
        result = resp.json()["result"]
        assert "summary" in result

    def test_exploitability_task(self, client):
        """Test running Exploitability analysis via task API."""
        if not _openspiel_available(client):
            pytest.skip("OpenSpiel plugin not running or not available on this platform")

        game_id = self._upload_efg_game(client)

        # Submit Exploitability task
        resp = client.post(
            "/api/tasks",
            params={
                "game_id": game_id,
                "plugin": "Exploitability",
            },
        )
        assert resp.status_code == 200, f"Task submission failed: {resp.text}"
        task_id = resp.json()["id"]

        # Poll for completion
        status = None
        for _ in range(50):
            resp = client.get(f"/api/tasks/{task_id}")
            assert resp.status_code == 200
            status = resp.json()["status"]
            if status in ("completed", "failed"):
                break
            time.sleep(0.2)

        assert status == "completed", f"Task did not complete: {status}"
        result = resp.json()["result"]
        assert "nash_conv" in result.get("details", {})

    def test_cfr_convergence_task(self, client):
        """Test running CFR Convergence analysis via task API."""
        if not _openspiel_available(client):
            pytest.skip("OpenSpiel plugin not running or not available on this platform")

        game_id = self._upload_efg_game(client)

        # Submit CFR Convergence task
        resp = client.post(
            "/api/tasks",
            params={
                "game_id": game_id,
                "plugin": "CFR Convergence",
                "iterations": 100,
            },
        )
        assert resp.status_code == 200, f"Task submission failed: {resp.text}"
        task_id = resp.json()["id"]

        # Poll for completion
        status = None
        for _ in range(50):
            resp = client.get(f"/api/tasks/{task_id}")
            assert resp.status_code == 200
            status = resp.json()["status"]
            if status in ("completed", "failed"):
                break
            time.sleep(0.2)

        assert status == "completed", f"Task did not complete: {status}"
        result = resp.json()["result"]
        assert "convergence_history" in result.get("details", {})
        assert "final_exploitability" in result.get("details", {})
