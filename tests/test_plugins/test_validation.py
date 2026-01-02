"""Tests for the validation plugin."""
import pytest

from app.core.registry import AnalysisResult
from app.models.game import Action, DecisionNode, Game, Outcome
from app.plugins.validation import ValidationPlugin


@pytest.fixture
def plugin() -> ValidationPlugin:
    return ValidationPlugin()


@pytest.fixture
def valid_game() -> Game:
    """A minimal valid game."""
    return Game(
        id="valid-game",
        title="Valid Game",
        players=["Alice", "Bob"],
        root="n_start",
        nodes={
            "n_start": DecisionNode(
                id="n_start",
                player="Alice",
                actions=[
                    Action(label="Left", target="o_left"),
                    Action(label="Right", target="o_right"),
                ],
            ),
        },
        outcomes={
            "o_left": Outcome(label="Left", payoffs={"Alice": 1, "Bob": 0}),
            "o_right": Outcome(label="Right", payoffs={"Alice": 0, "Bob": 1}),
        },
    )


class TestValidationPlugin:
    def test_plugin_metadata(self, plugin: ValidationPlugin):
        assert plugin.name == "Validation"
        assert plugin.continuous is True
        assert "extensive" in plugin.applicable_to

    def test_can_run_always_true(self, plugin: ValidationPlugin, valid_game: Game):
        assert plugin.can_run(valid_game) is True

    def test_valid_game_passes(self, plugin: ValidationPlugin, valid_game: Game):
        result = plugin.run(valid_game)
        assert isinstance(result, AnalysisResult)
        assert result.details["errors"] == []
        assert result.details["warnings"] == []
        assert result.summary == "Valid"

    def test_missing_root_node(self, plugin: ValidationPlugin):
        game = Game(
            id="bad-root",
            title="Bad Root",
            players=["Alice", "Bob"],
            root="nonexistent",
            nodes={},
            outcomes={},
        )
        result = plugin.run(game)
        assert len(result.details["errors"]) > 0
        assert "nonexistent" in result.details["errors"][0]
        assert "Invalid" in result.summary

    def test_action_with_invalid_target(self, plugin: ValidationPlugin):
        game = Game(
            id="bad-target",
            title="Bad Target",
            players=["Alice", "Bob"],
            root="n_start",
            nodes={
                "n_start": DecisionNode(
                    id="n_start",
                    player="Alice",
                    actions=[Action(label="Go", target="nowhere")],
                ),
            },
            outcomes={},
        )
        result = plugin.run(game)
        assert len(result.details["errors"]) > 0
        assert "nowhere" in str(result.details["errors"])

    def test_outcome_missing_player_payoff(self, plugin: ValidationPlugin):
        game = Game(
            id="missing-payoff",
            title="Missing Payoff",
            players=["Alice", "Bob"],
            root="n_start",
            nodes={
                "n_start": DecisionNode(
                    id="n_start",
                    player="Alice",
                    actions=[Action(label="Go", target="o_end")],
                ),
            },
            outcomes={
                "o_end": Outcome(label="End", payoffs={"Alice": 1}),  # Missing Bob
            },
        )
        result = plugin.run(game)
        assert len(result.details["errors"]) > 0
        assert "Bob" in str(result.details["errors"])

    def test_unreachable_node_warning(self, plugin: ValidationPlugin, valid_game: Game):
        # Add an orphan node
        valid_game.nodes["orphan"] = DecisionNode(
            id="orphan",
            player="Alice",
            actions=[Action(label="X", target="o_left")],
        )
        result = plugin.run(valid_game)
        assert len(result.details["warnings"]) > 0
        assert "orphan" in str(result.details["warnings"])
        assert "Valid with" in result.summary

    def test_single_player_warning(self, plugin: ValidationPlugin):
        game = Game(
            id="single-player",
            title="Single Player",
            players=["Alice"],
            root="n_start",
            nodes={
                "n_start": DecisionNode(
                    id="n_start",
                    player="Alice",
                    actions=[Action(label="Go", target="o_end")],
                ),
            },
            outcomes={
                "o_end": Outcome(label="End", payoffs={"Alice": 1}),
            },
        )
        result = plugin.run(game)
        assert len(result.details["warnings"]) > 0
        assert "1 player" in str(result.details["warnings"])

    def test_node_without_actions(self, plugin: ValidationPlugin):
        game = Game(
            id="no-actions",
            title="No Actions",
            players=["Alice", "Bob"],
            root="n_start",
            nodes={
                "n_start": DecisionNode(
                    id="n_start",
                    player="Alice",
                    actions=[],
                ),
            },
            outcomes={},
        )
        result = plugin.run(game)
        assert len(result.details["errors"]) > 0
        assert "no actions" in str(result.details["errors"])
