"""Shared test fixtures for Game Theory Workbench."""
from __future__ import annotations

from pathlib import Path
import logging

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_game_store
from app.formats import parse_game, supported_formats
from app.main import app
from app.models import ExtensiveFormGame
from app.plugins import discover_plugins

logger = logging.getLogger(__name__)

# Discover local plugins (register Validation, Dominance, etc.)
# This normally happens during FastAPI lifespan startup, but tests
# may access the registry directly without using TestClient.
discover_plugins()


def _load_example_games() -> None:
    """Load example games from examples/ directory for tests."""
    examples_dir = Path(__file__).resolve().parent.parent / "examples"
    if not examples_dir.exists():
        return

    store = get_game_store()
    for ext in supported_formats():
        for file_path in examples_dir.glob(f"*{ext}"):
            try:
                content = file_path.read_text(encoding="utf-8")
                game = parse_game(content, file_path.name)
                if not store.get(game.id):
                    store.add(game)
            except Exception:
                logger.warning("Failed to load example game: %s", file_path)


# Ensure example games are loaded for tests (TestClient doesn't run startup events)
_load_example_games()


@pytest.fixture
def trust_game() -> ExtensiveFormGame:
    """Return the Trust Game for testing."""
    store = get_game_store()
    game = store.get("trust-game")
    assert game is not None, "Trust game not loaded"
    assert isinstance(game, ExtensiveFormGame), "Trust game should be extensive form"
    return game


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def clean_store():
    """Fixture that ensures a clean game store for testing."""
    store = get_game_store()
    # Store original games
    original_games = {g.id: g for g in [store.get(s.id) for s in store.list()]}

    yield store

    # Restore original state
    current_ids = {s.id for s in store.list()}
    for game_id in current_ids:
        if game_id not in original_games:
            store.remove(game_id)
    for game_id, game in original_games.items():
        if game_id not in current_ids and game is not None:
            store.add(game)
