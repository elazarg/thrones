"""Tests for NFG (Normal Form Game) parser."""
from __future__ import annotations

import pytest

from app.core.dependencies import PYGAMBIT_AVAILABLE
from app.models.extensive_form import ExtensiveFormGame
from app.models.normal_form import NormalFormGame

if PYGAMBIT_AVAILABLE:
    from app.formats.gambit.nfg import parse_nfg


# Sample NFG content for testing (payoff list format)
# Payoffs are in order: (C,C) (C,D) (D,C) (D,D) - each pair is (P1, P2)
PRISONERS_DILEMMA_NFG = '''\
NFG 1 R "Prisoner's Dilemma" { "Player 1" "Player 2" }
{ { "Cooperate" "Defect" } { "Cooperate" "Defect" } }

3 3 0 5 5 0 1 1
'''

# Matching Pennies: (H,H) (H,T) (T,H) (T,T)
MATCHING_PENNIES_NFG = '''\
NFG 1 R "Matching Pennies" { "P1" "P2" }
{ { "Heads" "Tails" } { "Heads" "Tails" } }

1 -1 -1 1 -1 1 1 -1
'''


@pytest.mark.skipif(not PYGAMBIT_AVAILABLE, reason="pygambit not installed")
class TestNFGParser:
    def test_parse_prisoners_dilemma(self):
        """2-player games should be parsed as NormalFormGame."""
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        assert isinstance(game, NormalFormGame)
        assert game.title == "Prisoner's Dilemma"
        assert "Player 1" in game.players
        assert "Player 2" in game.players

    def test_parse_matching_pennies(self):
        game = parse_nfg(MATCHING_PENNIES_NFG, "mp.nfg")
        assert isinstance(game, NormalFormGame)
        assert game.title == "Matching Pennies"
        assert len(game.players) == 2

    def test_normal_form_structure(self):
        """2-player NFG should have proper matrix structure."""
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        assert isinstance(game, NormalFormGame)
        # Should have 2 strategies per player
        assert len(game.strategies[0]) == 2  # Cooperate, Defect
        assert len(game.strategies[1]) == 2  # Cooperate, Defect
        # Should have 2x2 payoff matrix
        assert len(game.payoffs) == 2
        assert len(game.payoffs[0]) == 2

    def test_strategies_correct(self):
        """Check strategy labels are preserved."""
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        assert "Cooperate" in game.strategies[0]
        assert "Defect" in game.strategies[0]
        assert "Cooperate" in game.strategies[1]
        assert "Defect" in game.strategies[1]

    def test_payoffs_are_correct(self):
        """Check that payoffs match the NFG specification as read by pygambit."""
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        # Verify payoffs match what pygambit provides from the NFG file
        # Note: The ordering comes from pygambit's interpretation of the NFG format
        assert game.payoffs[0][0] == (3.0, 3.0)  # (C,C)
        assert game.payoffs[0][1] == (5.0, 0.0)  # (C,D) per pygambit
        assert game.payoffs[1][0] == (0.0, 5.0)  # (D,C) per pygambit
        assert game.payoffs[1][1] == (1.0, 1.0)  # (D,D)

    def test_payoff_methods(self):
        """Test payoff accessor methods."""
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        # Test accessor methods work correctly
        assert game.row_player_payoff(0, 0) == 3.0  # (C,C) P1 payoff
        assert game.col_player_payoff(0, 0) == 3.0  # (C,C) P2 payoff
        assert game.get_payoff(1, 1) == (1.0, 1.0)  # (D,D)

    def test_nfg_games_have_tags(self):
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        assert "nfg" in game.tags
        assert "strategic-form" in game.tags
        assert "imported" in game.tags

    def test_parse_invalid_nfg_raises_error(self):
        with pytest.raises(Exception):
            parse_nfg("not valid nfg", "invalid.nfg")

    def test_num_strategies_property(self):
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        assert game.num_strategies == (2, 2)


@pytest.mark.skipif(not PYGAMBIT_AVAILABLE, reason="pygambit not installed")
class TestNFGParserMultiplayer:
    """Tests for 3+ player NFG files (converted to extensive form)."""

    # 3-player game for testing extensive form conversion
    THREE_PLAYER_NFG = '''\
NFG 1 R "3-Player Game" { "P1" "P2" "P3" }
{ { "A" "B" } { "C" "D" } { "E" "F" } }

1 0 0 0 1 0 0 0 1 0 0 0 0 1 0 0 0 1 0 0 0 0 1 0
'''

    def test_three_player_returns_extensive_form(self):
        """3+ player games should be converted to extensive form."""
        game = parse_nfg(self.THREE_PLAYER_NFG, "3p.nfg")
        assert isinstance(game, ExtensiveFormGame)
        assert len(game.players) == 3

    def test_three_player_has_tree_structure(self):
        """3-player extensive form should have proper tree structure."""
        game = parse_nfg(self.THREE_PLAYER_NFG, "3p.nfg")
        assert game.root in game.nodes
        root = game.nodes[game.root]
        assert root.player == "P1"
        assert len(root.actions) == 2
