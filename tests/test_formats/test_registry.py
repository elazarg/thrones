"""Tests for format registry."""
from __future__ import annotations

import pytest

from app.formats import parse_game, supported_formats


class TestFormatRegistry:
    def test_supported_formats_includes_json(self):
        formats = supported_formats()
        assert ".json" in formats

    def test_supported_formats_includes_efg(self):
        formats = supported_formats()
        assert ".efg" in formats

    def test_supported_formats_includes_nfg(self):
        formats = supported_formats()
        assert ".nfg" in formats

    def test_parse_game_unsupported_format(self):
        with pytest.raises(ValueError, match="Unsupported format"):
            parse_game("content", "file.xyz")

    def test_parse_game_infers_format_from_extension(self):
        game = parse_game(
            '{"id":"t","title":"T","players":["A"],"root":"n","nodes":{},"outcomes":{},"version":"v1","tags":[]}',
            "test.json",
        )
        assert game.title == "T"
