"""Tests for MAID Nash equilibrium analysis."""

import pytest

from pycid_plugin.nash import run_maid_nash


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
                    [1.0, 0.0, 0.0, 0.0],  # -3: Row=C, Col=D
                    [0.0, 0.0, 0.0, 1.0],  # -2: Both D
                    [0.0, 1.0, 0.0, 0.0],  # -1: Both C
                    [0.0, 0.0, 1.0, 0.0],  # 0: Row=D, Col=C
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


def test_run_maid_nash_returns_result(prisoners_dilemma_maid):
    """Test that MAID Nash analysis returns a valid result."""
    result = run_maid_nash(prisoners_dilemma_maid, {})

    assert "summary" in result
    assert "details" in result
    assert "equilibria" in result["details"]


def test_run_maid_nash_finds_equilibria(prisoners_dilemma_maid):
    """Test that MAID Nash analysis finds equilibria."""
    result = run_maid_nash(prisoners_dilemma_maid, {})

    equilibria = result["details"]["equilibria"]
    assert len(equilibria) > 0, "Should find at least one equilibrium"


def test_equilibrium_has_strategies(prisoners_dilemma_maid):
    """Test that equilibria have properly formatted strategies."""
    result = run_maid_nash(prisoners_dilemma_maid, {})

    equilibria = result["details"]["equilibria"]
    if len(equilibria) > 0:
        eq = equilibria[0]
        assert "strategies" in eq
        assert "description" in eq
        # Should have strategies for both decision nodes
        assert len(eq["strategies"]) == 2


def test_run_maid_nash_handles_missing_game():
    """Test that analysis handles invalid input gracefully."""
    result = run_maid_nash({}, {})

    # Should return error instead of crashing
    assert "summary" in result
    assert "Error" in result["summary"] or "equilibria" in result["details"]
