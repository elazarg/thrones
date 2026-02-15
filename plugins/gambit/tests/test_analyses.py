"""Tests for gambit plugin analyses (standalone, no main app dependency)."""

from __future__ import annotations

import pytest

from gambit_plugin.nash import run_nash
from gambit_plugin.iesds import run_iesds
from gambit_plugin.verify_profile import run_verify_profile

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def trust_game() -> dict:
    """Trust game in extensive form (as deserialized dict)."""
    return {
        "id": "trust-game",
        "title": "Trust Game",
        "players": ["Alice", "Bob"],
        "root": "n_start",
        "format_name": "extensive",
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
    }


@pytest.fixture
def prisoners_dilemma_nfg() -> dict:
    """Prisoner's Dilemma in normal form."""
    return {
        "id": "pd-nfg",
        "title": "Prisoner's Dilemma",
        "format_name": "normal",
        "players": ["Row", "Column"],
        "strategies": [["Cooperate", "Defect"], ["Cooperate", "Defect"]],
        "payoffs": [
            [(-1, -1), (-3, 0)],
            [(0, -3), (-2, -2)],
        ],
    }


@pytest.fixture
def matching_pennies_nfg() -> dict:
    """Matching Pennies in normal form."""
    return {
        "id": "mp-nfg",
        "title": "Matching Pennies",
        "format_name": "normal",
        "players": ["Matcher", "Mismatcher"],
        "strategies": [["Heads", "Tails"], ["Heads", "Tails"]],
        "payoffs": [
            [(1, -1), (-1, 1)],
            [(-1, 1), (1, -1)],
        ],
    }


# ---------------------------------------------------------------------------
# Nash tests
# ---------------------------------------------------------------------------


class TestNash:
    def test_trust_game(self, trust_game):
        result = run_nash(trust_game)
        assert "equilibria" in result["details"]
        assert len(result["details"]["equilibria"]) >= 1

    def test_trust_game_equilibrium_structure(self, trust_game):
        result = run_nash(trust_game)
        eq = result["details"]["equilibria"][0]
        assert "description" in eq
        assert "behavior_profile" in eq
        assert "payoffs" in eq
        assert "Alice" in eq["behavior_profile"]
        assert "Bob" in eq["behavior_profile"]

    def test_normal_form(self, prisoners_dilemma_nfg):
        result = run_nash(prisoners_dilemma_nfg)
        assert result["details"]["equilibria"]

    def test_quick_solver(self, trust_game):
        result = run_nash(trust_game, {"solver": "quick"})
        assert result["details"]["equilibria"]

    def test_pure_solver(self, trust_game):
        result = run_nash(trust_game, {"solver": "pure"})
        assert "equilibria" in result["details"]

    def test_summary_format(self, trust_game):
        result = run_nash(trust_game)
        assert "Nash equilibri" in result["summary"]


# ---------------------------------------------------------------------------
# IESDS tests
# ---------------------------------------------------------------------------


class TestIESDS:
    def test_prisoners_dilemma(self, prisoners_dilemma_nfg):
        result = run_iesds(prisoners_dilemma_nfg)
        eliminated = result["details"]["eliminated"]
        eliminated_strategies = [(e["player"], e["strategy"]) for e in eliminated]
        assert ("Row", "Cooperate") in eliminated_strategies
        assert ("Column", "Cooperate") in eliminated_strategies

    def test_no_elimination(self, matching_pennies_nfg):
        result = run_iesds(matching_pennies_nfg)
        assert len(result["details"]["eliminated"]) == 0

    def test_summary(self, prisoners_dilemma_nfg):
        result = run_iesds(prisoners_dilemma_nfg)
        assert (
            "eliminated" in result["summary"].lower()
            or "Eliminated" in result["summary"]
        )


# ---------------------------------------------------------------------------
# Verify Profile tests
# ---------------------------------------------------------------------------


class TestVerifyProfile:
    def test_equilibrium_detected(self, prisoners_dilemma_nfg):
        result = run_verify_profile(
            prisoners_dilemma_nfg,
            {
                "profile": {
                    "Row": {"Cooperate": 0.0, "Defect": 1.0},
                    "Column": {"Cooperate": 0.0, "Defect": 1.0},
                }
            },
        )
        assert result["details"]["is_equilibrium"] is True

    def test_non_equilibrium_detected(self, prisoners_dilemma_nfg):
        result = run_verify_profile(
            prisoners_dilemma_nfg,
            {
                "profile": {
                    "Row": {"Cooperate": 1.0, "Defect": 0.0},
                    "Column": {"Cooperate": 1.0, "Defect": 0.0},
                }
            },
        )
        assert result["details"]["is_equilibrium"] is False

    def test_requires_profile(self, prisoners_dilemma_nfg):
        with pytest.raises(ValueError, match="profile"):
            run_verify_profile(prisoners_dilemma_nfg, {})

    def test_mixed_equilibrium(self, matching_pennies_nfg):
        result = run_verify_profile(
            matching_pennies_nfg,
            {
                "profile": {
                    "Matcher": {"Heads": 0.5, "Tails": 0.5},
                    "Mismatcher": {"Heads": 0.5, "Tails": 0.5},
                }
            },
        )
        assert result["details"]["is_equilibrium"] is True
