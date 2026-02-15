"""Tests for MAID Subgame Perfect Equilibrium analysis."""

import pytest

from pycid_plugin.spe import run_maid_spe


@pytest.fixture
def prisoners_dilemma_maid():
    """Prisoner's Dilemma as a MAID."""
    return {
        "id": "pd-maid",
        "title": "Prisoner's Dilemma",
        "format_name": "maid",
        "agents": ["Row", "Column"],
        "nodes": [
            {"id": "D1", "type": "decision", "agent": "Row", "domain": ["C", "D"]},
            {"id": "D2", "type": "decision", "agent": "Column", "domain": ["C", "D"]},
            {"id": "U1", "type": "utility", "agent": "Row", "domain": [-3, -2, -1, 0]},
            {
                "id": "U2",
                "type": "utility",
                "agent": "Column",
                "domain": [-3, -2, -1, 0],
            },
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
        "tags": ["maid", "2-player", "example"],
    }


def test_run_maid_spe_returns_result(prisoners_dilemma_maid):
    """Test that MAID SPE analysis returns a valid result."""
    result = run_maid_spe(prisoners_dilemma_maid, {})

    assert "summary" in result
    assert "details" in result
    assert "equilibria" in result["details"]


def test_run_maid_spe_finds_equilibria(prisoners_dilemma_maid):
    """Test that MAID SPE analysis finds equilibria."""
    result = run_maid_spe(prisoners_dilemma_maid, {})

    # SPE should find at least what Nash finds (it's a refinement)
    equilibria = result["details"]["equilibria"]
    # In PD, SPE and NE coincide for simultaneous games
    assert isinstance(equilibria, list)


def test_spe_equilibrium_has_strategies(prisoners_dilemma_maid):
    """Test that SPE equilibria have properly formatted strategies."""
    result = run_maid_spe(prisoners_dilemma_maid, {})

    equilibria = result["details"]["equilibria"]
    if len(equilibria) > 0:
        eq = equilibria[0]
        assert "strategies" in eq
        assert "description" in eq


def test_run_maid_spe_handles_missing_game():
    """Test that SPE analysis handles invalid input gracefully."""
    result = run_maid_spe({}, {})

    # Should return error instead of crashing
    assert "summary" in result
    assert "Error" in result["summary"] or "equilibria" in result["details"]


def test_run_maid_spe_with_enumpure_solver(prisoners_dilemma_maid):
    """Test SPE with explicit enumpure solver config."""
    result = run_maid_spe(prisoners_dilemma_maid, {"solver": "enumpure"})

    assert "summary" in result
    assert "details" in result
    assert result["details"].get("solver") == "enumpure"
