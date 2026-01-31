"""Comprehensive IESDS tests for the gambit plugin."""

from __future__ import annotations

import pytest

from gambit_plugin.iesds import run_iesds
from gambit_plugin.strategies import enumerate_strategies, resolve_payoffs
from gambit_plugin.gambit_utils import normal_form_to_gambit

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def prisoners_dilemma_nfg() -> dict:
    """Prisoner's Dilemma - D strictly dominates C for both players."""
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
def prisoners_dilemma_efg() -> dict:
    """Prisoner's Dilemma in extensive form with information sets (simultaneous)."""
    return {
        "id": "pd-efg",
        "title": "Prisoner's Dilemma",
        "format_name": "extensive",
        "players": ["P1", "P2"],
        "root": "n_p1",
        "nodes": {
            "n_p1": {
                "id": "n_p1",
                "player": "P1",
                "actions": [
                    {"label": "C", "target": "n_p2_c"},
                    {"label": "D", "target": "n_p2_d"},
                ],
            },
            "n_p2_c": {
                "id": "n_p2_c",
                "player": "P2",
                "information_set": "h_p2",
                "actions": [
                    {"label": "C", "target": "o_cc"},
                    {"label": "D", "target": "o_cd"},
                ],
            },
            "n_p2_d": {
                "id": "n_p2_d",
                "player": "P2",
                "information_set": "h_p2",
                "actions": [
                    {"label": "C", "target": "o_dc"},
                    {"label": "D", "target": "o_dd"},
                ],
            },
        },
        "outcomes": {
            "o_cc": {"label": "CC", "payoffs": {"P1": -1, "P2": -1}},
            "o_cd": {"label": "CD", "payoffs": {"P1": -3, "P2": 0}},
            "o_dc": {"label": "DC", "payoffs": {"P1": 0, "P2": -3}},
            "o_dd": {"label": "DD", "payoffs": {"P1": -2, "P2": -2}},
        },
    }


@pytest.fixture
def matching_pennies_nfg() -> dict:
    """Matching Pennies - no dominated strategies."""
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


@pytest.fixture
def dominated_game_nfg() -> dict:
    """A game where one strategy is strictly dominated."""
    return {
        "id": "dominated-nfg",
        "title": "Dominated Strategy Game",
        "format_name": "normal",
        "players": ["Row", "Column"],
        "strategies": [["Good", "Bad"], ["Left", "Right"]],
        "payoffs": [
            [(3, 1), (3, 1)],  # Good gives 3 regardless
            [(1, 1), (1, 1)],  # Bad gives 1 regardless - dominated!
        ],
    }


@pytest.fixture
def iterated_dominance_game() -> dict:
    """A game requiring multiple rounds of elimination."""
    return {
        "id": "iterated",
        "title": "Iterated Dominance",
        "format_name": "normal",
        "players": ["Row", "Column"],
        "strategies": [["A", "B", "C"], ["X", "Y"]],
        "payoffs": [
            [(4, 3), (2, 2)],  # A
            [(3, 1), (3, 4)],  # B
            [(1, 2), (1, 3)],  # C - dominated by A (and B)
        ],
    }


# ---------------------------------------------------------------------------
# IESDS analysis tests
# ---------------------------------------------------------------------------


class TestIESDSPlugin:
    def test_prisoners_dilemma_nfg_elimination(self, prisoners_dilemma_nfg):
        """In PD, Cooperate is dominated by Defect for both players."""
        result = run_iesds(prisoners_dilemma_nfg)

        eliminated = result["details"]["eliminated"]
        surviving = result["details"]["surviving"]

        eliminated_strategies = [(e["player"], e["strategy"]) for e in eliminated]
        assert ("Row", "Cooperate") in eliminated_strategies
        assert ("Column", "Cooperate") in eliminated_strategies

        assert surviving["Row"] == ["Defect"]
        assert surviving["Column"] == ["Defect"]

    def test_prisoners_dilemma_efg_elimination(self, prisoners_dilemma_efg):
        """EFG version should also eliminate C for both players."""
        result = run_iesds(prisoners_dilemma_efg)

        eliminated = result["details"]["eliminated"]
        assert len(eliminated) >= 2

    def test_matching_pennies_no_elimination(self, matching_pennies_nfg):
        """Matching Pennies has no dominated strategies."""
        result = run_iesds(matching_pennies_nfg)

        eliminated = result["details"]["eliminated"]
        surviving = result["details"]["surviving"]

        assert len(eliminated) == 0
        assert surviving["Matcher"] == ["Heads", "Tails"]
        assert surviving["Mismatcher"] == ["Heads", "Tails"]

    def test_single_dominated_strategy(self, dominated_game_nfg):
        """Should eliminate the strictly dominated strategy."""
        result = run_iesds(dominated_game_nfg)

        eliminated = result["details"]["eliminated"]
        surviving = result["details"]["surviving"]

        row_eliminated = [e for e in eliminated if e["player"] == "Row"]
        assert len(row_eliminated) == 1
        assert row_eliminated[0]["strategy"] == "Bad"

        col_eliminated = [e for e in eliminated if e["player"] == "Column"]
        assert len(col_eliminated) == 0

        assert surviving["Row"] == ["Good"]
        assert surviving["Column"] == ["Left", "Right"]

    def test_rounds_counted_correctly(self, prisoners_dilemma_nfg):
        """Should track elimination rounds."""
        result = run_iesds(prisoners_dilemma_nfg)
        rounds = result["details"]["rounds"]
        assert rounds >= 1

    def test_summarize_no_eliminations(self, matching_pennies_nfg):
        """Summary should indicate no dominated strategies."""
        result = run_iesds(matching_pennies_nfg)
        assert (
            "No dominated strategies" in result["summary"]
            or "no dominated" in result["summary"].lower()
        )

    def test_summarize_with_eliminations(self, prisoners_dilemma_nfg):
        """Summary should indicate strategies were eliminated."""
        result = run_iesds(prisoners_dilemma_nfg)
        assert (
            "eliminated" in result["summary"].lower()
            or "Eliminated" in result["summary"]
        )

    def test_result_structure(self, prisoners_dilemma_nfg):
        """Result should have the expected dict structure."""
        result = run_iesds(prisoners_dilemma_nfg)
        assert "summary" in result
        assert "details" in result
        assert "eliminated" in result["details"]
        assert "rounds" in result["details"]
        assert "surviving" in result["details"]


# ---------------------------------------------------------------------------
# IESDS internals tests
# ---------------------------------------------------------------------------


class TestIESDSPluginInternals:
    def test_enumerate_strategies_efg(self, prisoners_dilemma_efg):
        """Should enumerate strategies respecting information sets."""
        strategies = enumerate_strategies(prisoners_dilemma_efg)
        assert len(strategies["P1"]) == 2
        assert len(strategies["P2"]) == 2

    def test_strategy_consistency_in_info_sets(self, prisoners_dilemma_efg):
        """Strategies should assign same action to nodes in same info set."""
        strategies = enumerate_strategies(prisoners_dilemma_efg)
        for strategy in strategies["P2"]:
            assert strategy["n_p2_c"] == strategy["n_p2_d"]

    def test_resolve_payoffs(self, prisoners_dilemma_efg):
        """Should correctly resolve payoffs for a strategy profile."""
        profile = {
            "P1": {"n_p1": "D"},
            "P2": {"n_p2_c": "C", "n_p2_d": "C"},
        }
        payoffs = resolve_payoffs(prisoners_dilemma_efg, profile)
        assert payoffs["P1"] == 0
        assert payoffs["P2"] == -3

    def test_normal_form_to_gambit_conversion(self, prisoners_dilemma_nfg):
        """Should convert NormalFormGame dict to Gambit game correctly."""
        gambit_game = normal_form_to_gambit(prisoners_dilemma_nfg)
        assert gambit_game.title == "Prisoner's Dilemma"
        assert len(gambit_game.players) == 2
        assert gambit_game.players[0].label == "Row"
        assert gambit_game.players[1].label == "Column"


# ---------------------------------------------------------------------------
# Iterative elimination tests
# ---------------------------------------------------------------------------


class TestIESDSIterativeElimination:
    def test_multi_round_elimination(self, iterated_dominance_game):
        """Should perform multiple rounds of elimination."""
        result = run_iesds(iterated_dominance_game)

        eliminated = result["details"]["eliminated"]
        row_eliminated = [e["strategy"] for e in eliminated if e["player"] == "Row"]
        assert "C" in row_eliminated
