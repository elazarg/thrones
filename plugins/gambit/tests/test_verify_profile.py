"""Comprehensive Verify Profile tests for the gambit plugin."""
from __future__ import annotations

import pytest

from gambit_plugin.verify_profile import run_verify_profile
from gambit_plugin.gambit_utils import normal_form_to_gambit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def matching_pennies_nfg() -> dict:
    """Matching Pennies - unique mixed equilibrium at (0.5, 0.5)."""
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
def prisoners_dilemma_nfg() -> dict:
    """Prisoner's Dilemma - unique equilibrium at (Defect, Defect)."""
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
def battle_of_sexes_nfg() -> dict:
    """Battle of the Sexes - two pure equilibria and one mixed."""
    return {
        "id": "bos-nfg",
        "title": "Battle of the Sexes",
        "format_name": "normal",
        "players": ["Alice", "Bob"],
        "strategies": [["Opera", "Football"], ["Opera", "Football"]],
        "payoffs": [
            [(3, 2), (0, 0)],
            [(0, 0), (2, 3)],
        ],
    }


@pytest.fixture
def trust_game_efg() -> dict:
    """Trust Game in extensive form."""
    return {
        "id": "trust-efg",
        "title": "Trust Game",
        "format_name": "extensive",
        "players": ["Alice", "Bob"],
        "root": "n_alice",
        "nodes": {
            "n_alice": {
                "id": "n_alice",
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
                    {"label": "Honor", "target": "o_honor"},
                    {"label": "Betray", "target": "o_betray"},
                ],
            },
        },
        "outcomes": {
            "o_honor": {"label": "Honor", "payoffs": {"Alice": 1, "Bob": 1}},
            "o_betray": {"label": "Betray", "payoffs": {"Alice": -1, "Bob": 2}},
            "o_decline": {"label": "Decline", "payoffs": {"Alice": 0, "Bob": 0}},
        },
    }


# ---------------------------------------------------------------------------
# Verify Profile tests
# ---------------------------------------------------------------------------

class TestVerifyProfilePlugin:
    def test_requires_profile_config(self, matching_pennies_nfg):
        """Should raise error if no profile provided."""
        with pytest.raises(ValueError, match="profile"):
            run_verify_profile(matching_pennies_nfg, config=None)

        with pytest.raises(ValueError, match="profile"):
            run_verify_profile(matching_pennies_nfg, config={})

    def test_verify_pure_equilibrium_pd(self, prisoners_dilemma_nfg):
        """(Defect, Defect) is the unique Nash equilibrium in PD."""
        profile = {
            "Row": {"Cooperate": 0.0, "Defect": 1.0},
            "Column": {"Cooperate": 0.0, "Defect": 1.0},
        }
        result = run_verify_profile(prisoners_dilemma_nfg, config={"profile": profile})

        assert result["details"]["is_equilibrium"] is True
        assert result["details"]["max_regret"] < 1e-6
        assert "equilibrium" in result["summary"].lower()

    def test_verify_non_equilibrium_pd(self, prisoners_dilemma_nfg):
        """(Cooperate, Cooperate) is NOT an equilibrium."""
        profile = {
            "Row": {"Cooperate": 1.0, "Defect": 0.0},
            "Column": {"Cooperate": 1.0, "Defect": 0.0},
        }
        result = run_verify_profile(prisoners_dilemma_nfg, config={"profile": profile})

        assert result["details"]["is_equilibrium"] is False
        assert result["details"]["max_regret"] > 0
        assert "not" in result["summary"].lower() or "regret" in result["summary"].lower()

    def test_verify_mixed_equilibrium_matching_pennies(self, matching_pennies_nfg):
        """(0.5, 0.5) for both players is the unique mixed equilibrium."""
        profile = {
            "Matcher": {"Heads": 0.5, "Tails": 0.5},
            "Mismatcher": {"Heads": 0.5, "Tails": 0.5},
        }
        result = run_verify_profile(matching_pennies_nfg, config={"profile": profile})

        assert result["details"]["is_equilibrium"] is True
        assert result["details"]["max_regret"] < 1e-6

    def test_verify_non_equilibrium_mixed_matching_pennies(self, matching_pennies_nfg):
        """Unbalanced mixed strategy is not an equilibrium."""
        profile = {
            "Matcher": {"Heads": 0.7, "Tails": 0.3},
            "Mismatcher": {"Heads": 0.5, "Tails": 0.5},
        }
        result = run_verify_profile(matching_pennies_nfg, config={"profile": profile})

        assert result["details"]["is_equilibrium"] is False

    def test_verify_pure_equilibrium_bos(self, battle_of_sexes_nfg):
        """(Opera, Opera) is a pure Nash equilibrium in Battle of Sexes."""
        profile = {
            "Alice": {"Opera": 1.0, "Football": 0.0},
            "Bob": {"Opera": 1.0, "Football": 0.0},
        }
        result = run_verify_profile(battle_of_sexes_nfg, config={"profile": profile})

        assert result["details"]["is_equilibrium"] is True

    def test_verify_second_pure_equilibrium_bos(self, battle_of_sexes_nfg):
        """(Football, Football) is also a pure Nash equilibrium."""
        profile = {
            "Alice": {"Opera": 0.0, "Football": 1.0},
            "Bob": {"Opera": 0.0, "Football": 1.0},
        }
        result = run_verify_profile(battle_of_sexes_nfg, config={"profile": profile})

        assert result["details"]["is_equilibrium"] is True

    def test_strategy_regrets_returned(self, prisoners_dilemma_nfg):
        """Should return per-strategy regrets."""
        profile = {
            "Row": {"Cooperate": 1.0, "Defect": 0.0},
            "Column": {"Cooperate": 1.0, "Defect": 0.0},
        }
        result = run_verify_profile(prisoners_dilemma_nfg, config={"profile": profile})

        regrets = result["details"]["strategy_regrets"]
        assert "Row" in regrets
        assert "Column" in regrets
        assert "Cooperate" in regrets["Row"]
        assert "Defect" in regrets["Row"]

    def test_payoffs_returned(self, prisoners_dilemma_nfg):
        """Should return expected payoffs for the profile."""
        profile = {
            "Row": {"Cooperate": 0.0, "Defect": 1.0},
            "Column": {"Cooperate": 0.0, "Defect": 1.0},
        }
        result = run_verify_profile(prisoners_dilemma_nfg, config={"profile": profile})

        payoffs = result["details"]["payoffs"]
        assert payoffs["Row"] == -2
        assert payoffs["Column"] == -2

    def test_result_structure(self, prisoners_dilemma_nfg):
        """Result should have the expected dict structure."""
        profile = {
            "Row": {"Cooperate": 0.0, "Defect": 1.0},
            "Column": {"Cooperate": 0.0, "Defect": 1.0},
        }
        result = run_verify_profile(prisoners_dilemma_nfg, config={"profile": profile})

        assert "summary" in result
        assert "details" in result
        assert "is_equilibrium" in result["details"]
        assert "max_regret" in result["details"]
        assert "strategy_regrets" in result["details"]
        assert "payoffs" in result["details"]


# ---------------------------------------------------------------------------
# Extensive form tests
# ---------------------------------------------------------------------------

class TestVerifyProfileExtensiveForm:
    def test_verify_equilibrium_efg(self, trust_game_efg):
        """(Don't, Betray) is the subgame perfect equilibrium."""
        profile = {
            "Alice": {"Don't": 1.0, "Trust": 0.0},
            "Bob": {"Betray": 1.0, "Honor": 0.0},
        }
        result = run_verify_profile(trust_game_efg, config={"profile": profile})

        assert result["details"]["is_equilibrium"] is True

    def test_non_equilibrium_efg(self, trust_game_efg):
        """(Trust, Honor) is not an equilibrium - Bob wants to deviate."""
        profile = {
            "Alice": {"Trust": 1.0, "Don't": 0.0},
            "Bob": {"Honor": 1.0, "Betray": 0.0},
        }
        result = run_verify_profile(trust_game_efg, config={"profile": profile})

        assert result["details"]["is_equilibrium"] is False


# ---------------------------------------------------------------------------
# Internals tests
# ---------------------------------------------------------------------------

class TestVerifyProfileInternals:
    def test_normal_form_to_gambit(self, matching_pennies_nfg):
        """Should convert NormalFormGame dict to Gambit format."""
        gambit_game = normal_form_to_gambit(matching_pennies_nfg)

        assert gambit_game.title == "Matching Pennies"
        assert len(gambit_game.players) == 2
        assert len(gambit_game.players[0].strategies) == 2
        assert len(gambit_game.players[1].strategies) == 2
