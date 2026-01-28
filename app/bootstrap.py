from __future__ import annotations

import logging

from app.core.paths import get_examples_dir
from app.core.store import game_store
from app.formats import parse_game, supported_formats
from app.plugins import discover_plugins

logger = logging.getLogger(__name__)

_plugins_discovered = False


def ensure_plugins_discovered() -> None:
    global _plugins_discovered
    if not _plugins_discovered:
        discover_plugins()
        _plugins_discovered = True


def load_example_games() -> None:
    examples_dir = get_examples_dir()
    if not examples_dir.exists():
        return

    for ext in supported_formats():
        for file_path in examples_dir.glob(f"*{ext}"):
            try:
                content = file_path.read_text(encoding="utf-8")
                game = parse_game(content, file_path.name)
                game_store.add(game)
                logger.info("Loaded example: %s", file_path.name)
            except Exception as e:
                logger.warning("Failed to load %s: %s", file_path, e)
