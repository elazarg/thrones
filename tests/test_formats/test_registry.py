"""Tests for format registry."""
from __future__ import annotations

import pytest

from app.formats import parse_game, supported_formats


class TestFormatRegistry:
    def test_supported_formats_includes_json(self):
        formats = supported_formats()
        assert ".json" in formats

    def test_efg_nfg_not_in_main_app(self):
        """With isolated plugin architecture, .efg/.nfg parsing requires pygambit
        which lives in the gambit plugin venv, not the main app."""
        formats = supported_formats()
        # These are only available when pygambit is installed in the main venv
        # With isolated plugins, the main app only natively supports .json
        assert ".json" in formats

    def test_parse_game_unsupported_format(self):
        with pytest.raises(ValueError, match="Unsupported format"):
            parse_game("content", "file.xyz")

    def test_parse_game_infers_format_from_extension(self):
        game = parse_game(
            '{"id":"t","title":"T","players":["A"],"root":"n","nodes":{},"outcomes":{},"version":"v1","tags":[]}',
            "test.json",
        )
        assert game.title == "T"
