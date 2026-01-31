"""Tests for EFG and NFG format parsers in the gambit plugin."""

from __future__ import annotations

import pytest

from gambit_plugin.parsers import parse_efg, parse_nfg

# ---------------------------------------------------------------------------
# EFG test data
# ---------------------------------------------------------------------------

TRUST_GAME_EFG = """\
EFG 2 R "Trust Game" { "Alice" "Bob" }
p "" 1 1 "" { "Trust" "Don't" } 0
p "" 2 1 "" { "Honor" "Betray" } 0
t "" 1 "Cooperate" { 1, 1 }
t "" 2 "Betray" { -1, 2 }
t "" 3 "Decline" { 0, 0 }
"""

SIMPLE_GAME_EFG = """\
EFG 2 R "Simple" { "P1" "P2" }
p "" 1 1 "" { "L" "R" } 0
t "" 1 "Left" { 1, 0 }
t "" 2 "Right" { 0, 1 }
"""


# ---------------------------------------------------------------------------
# NFG test data
# ---------------------------------------------------------------------------

PRISONERS_DILEMMA_NFG = """\
NFG 1 R "Prisoner's Dilemma" { "Player 1" "Player 2" }
{ { "Cooperate" "Defect" } { "Cooperate" "Defect" } }

3 3 0 5 5 0 1 1
"""

MATCHING_PENNIES_NFG = """\
NFG 1 R "Matching Pennies" { "P1" "P2" }
{ { "Heads" "Tails" } { "Heads" "Tails" } }

1 -1 -1 1 -1 1 1 -1
"""

THREE_PLAYER_NFG = """\
NFG 1 R "3-Player Game" { "P1" "P2" "P3" }
{ { "A" "B" } { "C" "D" } { "E" "F" } }

1 0 0 0 1 0 0 0 1 0 0 0 0 1 0 0 0 1 0 0 0 0 1 0
"""


# ---------------------------------------------------------------------------
# EFG parser tests
# ---------------------------------------------------------------------------


class TestEFGParser:
    def test_parse_simple_game(self):
        game = parse_efg(SIMPLE_GAME_EFG, "simple.efg")
        assert game["format_name"] == "extensive"
        assert game["title"] == "Simple"
        assert game["players"] == ["P1", "P2"]
        assert len(game["nodes"]) >= 1
        assert len(game["outcomes"]) >= 2

    def test_parse_trust_game(self):
        game = parse_efg(TRUST_GAME_EFG, "trust.efg")
        assert game["title"] == "Trust Game"
        assert "Alice" in game["players"]
        assert "Bob" in game["players"]

    def test_game_has_valid_structure(self):
        game = parse_efg(SIMPLE_GAME_EFG, "simple.efg")
        # Root should exist and be a valid node
        assert game["root"] in game["nodes"]
        root = game["nodes"][game["root"]]
        assert root["player"] in game["players"]
        assert len(root["actions"]) > 0

    def test_actions_point_to_valid_targets(self):
        game = parse_efg(SIMPLE_GAME_EFG, "simple.efg")
        for node in game["nodes"].values():
            for action in node["actions"]:
                target = action["target"]
                assert (
                    target in game["nodes"] or target in game["outcomes"]
                ), f"Invalid target: {target}"

    def test_outcomes_have_payoffs_for_all_players(self):
        game = parse_efg(TRUST_GAME_EFG, "trust.efg")
        for outcome in game["outcomes"].values():
            for player in game["players"]:
                assert player in outcome["payoffs"]

    def test_imported_games_have_efg_tag(self):
        game = parse_efg(SIMPLE_GAME_EFG, "simple.efg")
        assert "efg" in game["tags"]
        assert "imported" in game["tags"]

    def test_parse_invalid_efg_raises_error(self):
        with pytest.raises(Exception):
            parse_efg("not a valid efg file", "invalid.efg")

    def test_parse_empty_string_raises_error(self):
        with pytest.raises(Exception):
            parse_efg("", "empty.efg")


# ---------------------------------------------------------------------------
# NFG parser tests
# ---------------------------------------------------------------------------


class TestNFGParser:
    def test_parse_prisoners_dilemma(self):
        """2-player games should be parsed as NormalFormGame dict."""
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        assert game["format_name"] == "normal"
        assert game["title"] == "Prisoner's Dilemma"
        assert "Player 1" in game["players"]
        assert "Player 2" in game["players"]

    def test_parse_matching_pennies(self):
        game = parse_nfg(MATCHING_PENNIES_NFG, "mp.nfg")
        assert game["format_name"] == "normal"
        assert game["title"] == "Matching Pennies"
        assert len(game["players"]) == 2

    def test_normal_form_structure(self):
        """2-player NFG should have proper matrix structure."""
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        assert game["format_name"] == "normal"
        assert len(game["strategies"][0]) == 2  # Cooperate, Defect
        assert len(game["strategies"][1]) == 2
        assert len(game["payoffs"]) == 2
        assert len(game["payoffs"][0]) == 2

    def test_strategies_correct(self):
        """Check strategy labels are preserved."""
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        assert "Cooperate" in game["strategies"][0]
        assert "Defect" in game["strategies"][0]
        assert "Cooperate" in game["strategies"][1]
        assert "Defect" in game["strategies"][1]

    def test_payoffs_are_correct(self):
        """Check that payoffs match the NFG specification as read by pygambit."""
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        # Payoffs are [p1, p2] lists now instead of tuples
        assert game["payoffs"][0][0] == [3.0, 3.0]  # (C,C)
        assert game["payoffs"][0][1] == [5.0, 0.0]  # (C,D) per pygambit
        assert game["payoffs"][1][0] == [0.0, 5.0]  # (D,C) per pygambit
        assert game["payoffs"][1][1] == [1.0, 1.0]  # (D,D)

    def test_nfg_games_have_tags(self):
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        assert "nfg" in game["tags"]
        assert "strategic-form" in game["tags"]
        assert "imported" in game["tags"]

    def test_parse_invalid_nfg_raises_error(self):
        with pytest.raises(Exception):
            parse_nfg("not valid nfg", "invalid.nfg")

    def test_has_id(self):
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        assert "id" in game
        assert len(game["id"]) > 0


class TestNFGParserMultiplayer:
    """Tests for 3+ player NFG files (converted to extensive form)."""

    def test_three_player_returns_extensive_form(self):
        """3+ player games should be converted to extensive form."""
        game = parse_nfg(THREE_PLAYER_NFG, "3p.nfg")
        assert game["format_name"] == "extensive"
        assert len(game["players"]) == 3

    def test_three_player_has_tree_structure(self):
        """3-player extensive form should have proper tree structure."""
        game = parse_nfg(THREE_PLAYER_NFG, "3p.nfg")
        assert game["root"] in game["nodes"]
        root = game["nodes"][game["root"]]
        assert root["player"] == "P1"
        assert len(root["actions"]) == 2
