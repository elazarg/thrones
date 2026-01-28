"""Integration tests for MAID to EFG conversion.

Tests the full flow from main app through the PyCID plugin for conversion.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.plugins import plugin_manager


@pytest.fixture(scope="module")
def client():
    """Create a test client with lifespan events (starts plugins)."""
    with TestClient(app) as c:
        yield c


def _pycid_available(client) -> bool:
    """Check if the pycid plugin is healthy."""
    for pp in plugin_manager.healthy_plugins():
        if pp.config.name == "pycid":
            return True
    return False


@pytest.fixture
def prisoners_dilemma_maid():
    """Prisoner's Dilemma as a MAID."""
    return {
        "id": "pd-maid",
        "title": "Prisoner's Dilemma (MAID)",
        "format_name": "maid",
        "agents": ["Row", "Column"],
        "nodes": [
            {"id": "D1", "type": "decision", "agent": "Row", "domain": ["C", "D"]},
            {"id": "D2", "type": "decision", "agent": "Column", "domain": ["C", "D"]},
            {"id": "U1", "type": "utility", "agent": "Row", "domain": [-3, -2, -1, 0]},
            {"id": "U2", "type": "utility", "agent": "Column", "domain": [-3, -2, -1, 0]},
        ],
        "edges": [
            {"source": "D1", "target": "U1"},
            {"source": "D1", "target": "U2"},
            {"source": "D2", "target": "U1"},
            {"source": "D2", "target": "U2"},
        ],
        "cpds": [
            {
                "node": "U1",
                "parents": ["D1", "D2"],
                "values": [
                    [1.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 1.0],
                    [0.0, 1.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0, 0.0],
                ],
            },
            {
                "node": "U2",
                "parents": ["D1", "D2"],
                "values": [
                    [1.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0, 0.0],
                    [0.0, 1.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 1.0],
                ],
            },
        ],
        "version": "v1",
        "tags": ["maid", "2-player", "example"],
    }


class TestConversionRegistration:
    """Test that conversions are registered from plugins."""

    def test_pycid_plugin_advertises_conversions(self, client):
        """PyCID plugin should advertise MAID to EFG conversion."""
        if not _pycid_available(client):
            pytest.skip("PyCID plugin not running")

        for pp in plugin_manager.healthy_plugins():
            if pp.config.name == "pycid":
                conversions = pp.info.get("conversions", [])
                assert len(conversions) > 0, "PyCID should advertise conversions"

                maid_to_efg = None
                for conv in conversions:
                    if conv["source"] == "maid" and conv["target"] == "extensive":
                        maid_to_efg = conv
                        break

                assert maid_to_efg is not None, "Should advertise maid to extensive conversion"
                return

        pytest.fail("PyCID plugin not found")

    def test_conversion_registered_in_registry(self, client):
        """MAID to EFG conversion should be registered in the main app."""
        if not _pycid_available(client):
            pytest.skip("PyCID plugin not running")

        from app.conversions.registry import conversion_registry

        # Check if conversion is registered
        key = ("maid", "extensive")
        assert key in conversion_registry._conversions, (
            "MAID to extensive conversion should be registered"
        )


class TestConversionFlow:
    """Test the full conversion flow."""

    def test_convert_maid_via_api(self, client, prisoners_dilemma_maid):
        """Test converting a MAID game via the conversion API."""
        if not _pycid_available(client):
            pytest.skip("PyCID plugin not running")

        from app.conversions.registry import conversion_registry
        from app.models.maid import MAIDGame

        # Create MAID game model
        maid_game = MAIDGame(**prisoners_dilemma_maid)

        # Check conversion is available
        check = conversion_registry.check(maid_game, "extensive")
        assert check.possible, f"Conversion should be possible: {check.blockers}"

        # Perform conversion
        result = conversion_registry.convert(maid_game, "extensive")

        assert result.format_name == "extensive"
        assert len(result.players) == 2
        assert result.root is not None
        assert len(result.nodes) > 0
        assert len(result.outcomes) > 0

    def test_converted_game_has_valid_structure(self, client, prisoners_dilemma_maid):
        """Test that converted game has a valid EFG structure."""
        if not _pycid_available(client):
            pytest.skip("PyCID plugin not running")

        from app.conversions.registry import conversion_registry
        from app.models.maid import MAIDGame

        maid_game = MAIDGame(**prisoners_dilemma_maid)
        efg = conversion_registry.convert(maid_game, "extensive")

        # Root should be in nodes
        assert efg.root in efg.nodes

        # All targets should be valid
        for node in efg.nodes.values():
            for action in node.actions:
                target = action.target
                assert target is not None
                assert target in efg.nodes or target in efg.outcomes

    def test_converted_game_preserves_payoff_structure(self, client, prisoners_dilemma_maid):
        """Test that outcomes have payoffs for all players."""
        if not _pycid_available(client):
            pytest.skip("PyCID plugin not running")

        from app.conversions.registry import conversion_registry
        from app.models.maid import MAIDGame

        maid_game = MAIDGame(**prisoners_dilemma_maid)
        efg = conversion_registry.convert(maid_game, "extensive")

        for outcome in efg.outcomes.values():
            assert len(outcome.payoffs) == len(efg.players)
            for player in efg.players:
                assert player in outcome.payoffs
