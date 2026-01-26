"""Tests for JSON format parser."""
from __future__ import annotations

import json

import pytest

from app.formats.json_format import parse_json, serialize_json
from app.models.game import Action, DecisionNode, ExtensiveFormGame, Outcome


class TestJSONParser:
    def test_parse_valid_json(self):
        game_data = {
            "id": "test-game",
            "title": "Test Game",
            "players": ["A", "B"],
            "root": "n1",
            "nodes": {
                "n1": {
                    "id": "n1",
                    "player": "A",
                    "actions": [{"label": "Go", "target": "o1"}],
                }
            },
            "outcomes": {"o1": {"label": "End", "payoffs": {"A": 1, "B": 2}}},
            "version": "v1",
            "tags": [],
        }
        content = json.dumps(game_data)
        game = parse_json(content, "test.json")
        assert isinstance(game, ExtensiveFormGame)
        assert game.title == "Test Game"
        assert game.players == ["A", "B"]

    def test_parse_invalid_json_raises_error(self):
        with pytest.raises(Exception):
            parse_json("not json", "bad.json")

    def test_parse_missing_required_fields(self):
        with pytest.raises(Exception):
            parse_json('{"title": "No players"}', "missing.json")


class TestJSONSerializer:
    def test_serialize_game(self):
        game = ExtensiveFormGame(
            id="test",
            title="Test",
            players=["X", "Y"],
            root="n1",
            nodes={
                "n1": DecisionNode(
                    id="n1",
                    player="X",
                    actions=[Action(label="Move", target="o1")],
                )
            },
            outcomes={"o1": Outcome(label="Done", payoffs={"X": 0, "Y": 0})},
            version="v1",
            tags=[],
        )
        content = serialize_json(game)
        data = json.loads(content)
        assert data["title"] == "Test"
        assert data["players"] == ["X", "Y"]

    def test_round_trip(self):
        """Parse → serialize → parse should give same game."""
        original = ExtensiveFormGame(
            id="round-trip",
            title="Round Trip Test",
            players=["Alice", "Bob"],
            root="n_root",
            nodes={
                "n_root": DecisionNode(
                    id="n_root",
                    player="Alice",
                    actions=[
                        Action(label="Left", target="o_left"),
                        Action(label="Right", target="o_right"),
                    ],
                )
            },
            outcomes={
                "o_left": Outcome(label="Left End", payoffs={"Alice": 1, "Bob": 0}),
                "o_right": Outcome(label="Right End", payoffs={"Alice": 0, "Bob": 1}),
            },
            version="v1",
            tags=["test"],
        )
        serialized = serialize_json(original)
        restored = parse_json(serialized, "restored.json")
        assert restored.title == original.title
        assert restored.players == original.players
        assert len(restored.nodes) == len(original.nodes)
        assert len(restored.outcomes) == len(original.outcomes)
