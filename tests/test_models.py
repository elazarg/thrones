"""Tests for game models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.game import Action, DecisionNode, Game, Outcome


class TestOutcome:
    def test_create_outcome(self):
        outcome = Outcome(label="Win", payoffs={"Alice": 1, "Bob": -1})
        assert outcome.label == "Win"
        assert outcome.payoffs == {"Alice": 1, "Bob": -1}

    def test_outcome_is_frozen(self):
        outcome = Outcome(label="Win", payoffs={"Alice": 1})
        with pytest.raises(ValidationError):
            outcome.label = "Lose"

    def test_outcome_forbids_extra(self):
        with pytest.raises(ValidationError):
            Outcome(label="Win", payoffs={"Alice": 1}, extra_field="bad")


class TestAction:
    def test_create_action(self):
        action = Action(label="Move", target="node_1")
        assert action.label == "Move"
        assert action.target == "node_1"
        assert action.probability is None
        assert action.warning is None

    def test_action_with_probability(self):
        action = Action(label="Move", target="node_1", probability=0.5)
        assert action.probability == 0.5

    def test_action_with_warning(self):
        action = Action(label="Bad", target="node_1", warning="Dominated")
        assert action.warning == "Dominated"


class TestDecisionNode:
    def test_create_decision_node(self):
        node = DecisionNode(
            id="n1",
            player="Alice",
            actions=[Action(label="Left", target="n2")],
        )
        assert node.id == "n1"
        assert node.player == "Alice"
        assert len(node.actions) == 1

    def test_decision_node_with_info_set(self):
        node = DecisionNode(
            id="n1",
            player="Alice",
            actions=[],
            information_set="h1",
        )
        assert node.information_set == "h1"


class TestGame:
    def test_trust_game_structure(self, trust_game: Game):
        assert trust_game.id == "trust-game"
        assert trust_game.title == "Trust Game"
        assert trust_game.players == ["Alice", "Bob"]
        assert trust_game.root == "n_start"
        assert len(trust_game.nodes) == 2
        assert len(trust_game.outcomes) == 3

    def test_reachable_outcomes(self, trust_game: Game):
        outcomes = trust_game.reachable_outcomes()
        assert len(outcomes) == 3
        labels = {o.label for o in outcomes}
        assert labels == {"Cooperate", "Betray", "Decline"}

    def test_game_is_frozen(self, trust_game: Game):
        with pytest.raises(ValidationError):
            trust_game.title = "New Title"

    def test_create_minimal_game(self):
        game = Game(
            id="test",
            title="Test",
            players=["P1"],
            root="start",
            nodes={
                "start": DecisionNode(
                    id="start",
                    player="P1",
                    actions=[Action(label="Go", target="end")],
                )
            },
            outcomes={"end": Outcome(label="End", payoffs={"P1": 0})},
        )
        assert game.version == "v1"
        assert game.tags == []
        outcomes = game.reachable_outcomes()
        assert len(outcomes) == 1
        assert outcomes[0].label == "End"
