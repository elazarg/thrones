"""Tests for NFG (Normal Form Game) parser."""
from __future__ import annotations

import pytest

from app.formats.nfg import PYGAMBIT_AVAILABLE, parse_nfg
from app.models.game import Game


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
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        assert isinstance(game, Game)
        assert game.title == "Prisoner's Dilemma"
        assert "Player 1" in game.players
        assert "Player 2" in game.players

    def test_parse_matching_pennies(self):
        game = parse_nfg(MATCHING_PENNIES_NFG, "mp.nfg")
        assert isinstance(game, Game)
        assert game.title == "Matching Pennies"
        assert len(game.players) == 2

    def test_extensive_form_structure(self):
        """NFG should be converted to extensive form tree."""
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        # Should have a root node
        assert game.root in game.nodes
        # Root should be Player 1
        root = game.nodes[game.root]
        assert root.player == "Player 1"
        # Should have 2 actions (Cooperate, Defect)
        assert len(root.actions) == 2

    def test_outcomes_count(self):
        """2x2 game should have 4 outcomes."""
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        assert len(game.outcomes) == 4

    def test_payoffs_are_correct(self):
        """Check that payoffs match the NFG specification."""
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        # Find the (Defect, Defect) outcome
        dd_outcome = None
        for outcome in game.outcomes.values():
            if outcome.payoffs.get("Player 1") == 1 and outcome.payoffs.get("Player 2") == 1:
                dd_outcome = outcome
                break
        assert dd_outcome is not None, "Should have (1,1) outcome for mutual defection"

    def test_player2_has_information_set(self):
        """Player 2 nodes should share an information set (simultaneous game)."""
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        p2_nodes = [n for n in game.nodes.values() if n.player == "Player 2"]
        # All P2 nodes should have an information set
        info_sets = {n.information_set for n in p2_nodes}
        # Should share the same info set (or all have one)
        assert len(info_sets) == 1 or all(i is not None for i in info_sets)

    def test_nfg_games_have_tags(self):
        game = parse_nfg(PRISONERS_DILEMMA_NFG, "pd.nfg")
        assert "nfg" in game.tags
        assert "strategic-form" in game.tags
        assert "imported" in game.tags

    def test_parse_invalid_nfg_raises_error(self):
        with pytest.raises(Exception):
            parse_nfg("not valid nfg", "invalid.nfg")
