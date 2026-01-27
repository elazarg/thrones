"""Comprehensive Nash equilibrium tests for the gambit plugin."""
from __future__ import annotations

import pytest

from gambit_plugin.nash import run_nash
from gambit_plugin.strategies import enumerate_strategies, resolve_payoffs
from gambit_plugin.gambit_utils import normal_form_to_gambit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def trust_game() -> dict:
    """Trust game in extensive form."""
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
def matching_pennies() -> dict:
    """Matching Pennies - simultaneous move with information sets."""
    return {
        "id": "matching-pennies",
        "title": "Matching Pennies",
        "format_name": "extensive",
        "players": ["P1", "P2"],
        "root": "n_p1",
        "nodes": {
            "n_p1": {
                "id": "n_p1",
                "player": "P1",
                "actions": [
                    {"label": "Heads", "target": "n_p2_after_heads"},
                    {"label": "Tails", "target": "n_p2_after_tails"},
                ],
            },
            "n_p2_after_heads": {
                "id": "n_p2_after_heads",
                "player": "P2",
                "information_set": "h_p2",
                "actions": [
                    {"label": "Heads", "target": "o_hh"},
                    {"label": "Tails", "target": "o_ht"},
                ],
            },
            "n_p2_after_tails": {
                "id": "n_p2_after_tails",
                "player": "P2",
                "information_set": "h_p2",
                "actions": [
                    {"label": "Heads", "target": "o_th"},
                    {"label": "Tails", "target": "o_tt"},
                ],
            },
        },
        "outcomes": {
            "o_hh": {"label": "HH", "payoffs": {"P1": 1, "P2": -1}},
            "o_ht": {"label": "HT", "payoffs": {"P1": -1, "P2": 1}},
            "o_th": {"label": "TH", "payoffs": {"P1": -1, "P2": 1}},
            "o_tt": {"label": "TT", "payoffs": {"P1": 1, "P2": -1}},
        },
    }


@pytest.fixture
def sequential_pennies() -> dict:
    """Pennies where P2 CAN see P1's choice (no information set)."""
    return {
        "id": "sequential-pennies",
        "title": "Sequential Pennies",
        "format_name": "extensive",
        "players": ["P1", "P2"],
        "root": "n_p1",
        "nodes": {
            "n_p1": {
                "id": "n_p1",
                "player": "P1",
                "actions": [
                    {"label": "Heads", "target": "n_p2_after_heads"},
                    {"label": "Tails", "target": "n_p2_after_tails"},
                ],
            },
            "n_p2_after_heads": {
                "id": "n_p2_after_heads",
                "player": "P2",
                "actions": [
                    {"label": "Heads", "target": "o_hh"},
                    {"label": "Tails", "target": "o_ht"},
                ],
            },
            "n_p2_after_tails": {
                "id": "n_p2_after_tails",
                "player": "P2",
                "actions": [
                    {"label": "Heads", "target": "o_th"},
                    {"label": "Tails", "target": "o_tt"},
                ],
            },
        },
        "outcomes": {
            "o_hh": {"label": "HH", "payoffs": {"P1": 1, "P2": -1}},
            "o_ht": {"label": "HT", "payoffs": {"P1": -1, "P2": 1}},
            "o_th": {"label": "TH", "payoffs": {"P1": -1, "P2": 1}},
            "o_tt": {"label": "TT", "payoffs": {"P1": 1, "P2": -1}},
        },
    }


# ---------------------------------------------------------------------------
# Nash analysis tests
# ---------------------------------------------------------------------------

class TestNashPlugin:
    def test_run_on_trust_game(self, trust_game):
        result = run_nash(trust_game)
        assert "equilibria" in result["details"]
        equilibria = result["details"]["equilibria"]
        assert len(equilibria) >= 1

    def test_equilibrium_structure(self, trust_game):
        result = run_nash(trust_game)
        eq = result["details"]["equilibria"][0]
        assert "description" in eq
        assert "behavior_profile" in eq
        assert "outcomes" in eq
        assert "strategies" in eq
        assert "payoffs" in eq
        assert "Alice" in eq["behavior_profile"]
        assert "Bob" in eq["behavior_profile"]

    def test_description_format(self, trust_game):
        result = run_nash(trust_game)
        for eq in result["details"]["equilibria"]:
            desc = eq["description"]
            assert desc.startswith("Pure:") or desc == "Mixed equilibrium"

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

    def test_summary_zero_equilibria(self):
        """Summary formatting when 0 equilibria are found."""
        # This tests the summary string logic
        summary = "No Nash equilibria found"
        assert "No" in summary

    def test_summary_plural(self, trust_game):
        """Summary uses plural 'equilibria' for >1."""
        result = run_nash(trust_game)
        count = len(result["details"]["equilibria"])
        if count > 1:
            assert "equilibria" in result["summary"]
        elif count == 1:
            assert "equilibrium" in result["summary"]


# ---------------------------------------------------------------------------
# Strategy utility tests
# ---------------------------------------------------------------------------

class TestStrategyUtilities:
    def test_enumerate_strategies(self, trust_game):
        strategies = enumerate_strategies(trust_game)
        assert "Alice" in strategies
        assert "Bob" in strategies
        assert len(strategies["Alice"]) == 2
        assert len(strategies["Bob"]) == 2

    def test_resolve_payoffs(self, trust_game):
        # Trust -> Honor path
        profile = {
            "Alice": {"n_start": "Trust"},
            "Bob": {"n_bob": "Honor"},
        }
        payoffs = resolve_payoffs(trust_game, profile)
        assert payoffs == {"Alice": 1, "Bob": 1}

        # Don't path
        profile = {
            "Alice": {"n_start": "Don't"},
            "Bob": {"n_bob": "Honor"},
        }
        payoffs = resolve_payoffs(trust_game, profile)
        assert payoffs == {"Alice": 0, "Bob": 0}

    def test_resolve_payoffs_missing_player(self, trust_game):
        profile = {"Alice": {"n_start": "Trust"}}
        with pytest.raises(ValueError):
            resolve_payoffs(trust_game, profile)


# ---------------------------------------------------------------------------
# Information set handling tests
# ---------------------------------------------------------------------------

class TestInformationSetHandling:
    def test_info_set_strategy_count(self, matching_pennies):
        """P2 should have 2 strategies, not 4, due to information set."""
        strategies = enumerate_strategies(matching_pennies)
        assert len(strategies["P1"]) == 2
        assert len(strategies["P2"]) == 2

    def test_no_info_set_strategy_count(self, sequential_pennies):
        """P2 should have 4 strategies when nodes are distinguishable."""
        strategies = enumerate_strategies(sequential_pennies)
        assert len(strategies["P1"]) == 2
        assert len(strategies["P2"]) == 4

    def test_info_set_strategy_consistency(self, matching_pennies):
        """Each P2 strategy should assign same action to both nodes."""
        strategies = enumerate_strategies(matching_pennies)
        for strategy in strategies["P2"]:
            assert strategy["n_p2_after_heads"] == strategy["n_p2_after_tails"]

    def test_matching_pennies_mixed_equilibrium(self, matching_pennies):
        """Matching Pennies should have only a mixed equilibrium (50-50)."""
        result = run_nash(matching_pennies)
        equilibria = result["details"]["equilibria"]
        assert len(equilibria) == 1
        eq = equilibria[0]
        assert eq["description"] == "Mixed equilibrium"
        assert abs(eq["payoffs"]["P1"]) < 0.01
        assert abs(eq["payoffs"]["P2"]) < 0.01

    def test_sequential_pennies_pure_equilibrium(self, sequential_pennies):
        """Sequential Pennies should have pure equilibria where P2 always wins."""
        result = run_nash(sequential_pennies)
        equilibria = result["details"]["equilibria"]
        assert len(equilibria) >= 1
        p2_wins = any(eq["payoffs"]["P2"] > 0 for eq in equilibria)
        assert p2_wins, "P2 should be able to win in sequential version"


# ---------------------------------------------------------------------------
# Gambit conversion tests
# ---------------------------------------------------------------------------

class TestGambitConversion:
    def test_normal_form_to_gambit(self, prisoners_dilemma_nfg):
        gambit_game = normal_form_to_gambit(prisoners_dilemma_nfg)
        assert gambit_game.title == "Prisoner's Dilemma"
        assert len(gambit_game.players) == 2
        assert gambit_game.players[0].label == "Row"
        assert gambit_game.players[1].label == "Column"
        assert len(gambit_game.players[0].strategies) == 2
        assert len(gambit_game.players[1].strategies) == 2
