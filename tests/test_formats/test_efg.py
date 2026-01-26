"""Tests for EFG (Extensive Form Game) parser."""
from __future__ import annotations

import pytest

from app.formats.gambit.efg import parse_efg
from app.models.extensive_form import ExtensiveFormGame
from app.core.dependencies import PYGAMBIT_AVAILABLE

# Sample EFG content for testing
TRUST_GAME_EFG = '''\
EFG 2 R "Trust Game" { "Alice" "Bob" }
p "" 1 1 "" { "Trust" "Don't" } 0
p "" 2 1 "" { "Honor" "Betray" } 0
t "" 1 "Cooperate" { 1, 1 }
t "" 2 "Betray" { -1, 2 }
t "" 3 "Decline" { 0, 0 }
'''

SIMPLE_GAME_EFG = '''\
EFG 2 R "Simple" { "P1" "P2" }
p "" 1 1 "" { "L" "R" } 0
t "" 1 "Left" { 1, 0 }
t "" 2 "Right" { 0, 1 }
'''


@pytest.mark.skipif(not PYGAMBIT_AVAILABLE, reason="pygambit not installed")
class TestEFGParser:
    def test_parse_simple_game(self):
        game = parse_efg(SIMPLE_GAME_EFG, "simple.efg")
        assert isinstance(game, ExtensiveFormGame)
        assert game.title == "Simple"
        assert game.players == ["P1", "P2"]
        assert len(game.nodes) >= 1
        assert len(game.outcomes) >= 2

    def test_parse_trust_game(self):
        game = parse_efg(TRUST_GAME_EFG, "trust.efg")
        assert isinstance(game, ExtensiveFormGame)
        assert game.title == "Trust Game"
        assert "Alice" in game.players
        assert "Bob" in game.players

    def test_game_has_valid_structure(self):
        game = parse_efg(SIMPLE_GAME_EFG, "simple.efg")
        # Root should exist and be a valid node
        assert game.root in game.nodes
        root = game.nodes[game.root]
        assert root.player in game.players
        assert len(root.actions) > 0

    def test_actions_point_to_valid_targets(self):
        game = parse_efg(SIMPLE_GAME_EFG, "simple.efg")
        for node in game.nodes.values():
            for action in node.actions:
                # Target should be either a node or an outcome
                assert (
                    action.target in game.nodes or action.target in game.outcomes
                ), f"Invalid target: {action.target}"

    def test_outcomes_have_payoffs_for_all_players(self):
        game = parse_efg(TRUST_GAME_EFG, "trust.efg")
        for outcome in game.outcomes.values():
            for player in game.players:
                assert player in outcome.payoffs

    def test_imported_games_have_efg_tag(self):
        game = parse_efg(SIMPLE_GAME_EFG, "simple.efg")
        assert "efg" in game.tags
        assert "imported" in game.tags

    def test_parse_invalid_efg_raises_error(self):
        with pytest.raises(Exception):  # pygambit raises various errors
            parse_efg("not a valid efg file", "invalid.efg")

    def test_parse_empty_string_raises_error(self):
        with pytest.raises(Exception):
            parse_efg("", "empty.efg")
