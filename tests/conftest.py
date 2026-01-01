"""Shared test fixtures for Game Theory Workbench."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.store import game_store
from app.main import TRUST_GAME, app
from app.models.game import Game


# Ensure Trust Game is loaded for tests (TestClient doesn't run startup events)
if not game_store.get(TRUST_GAME.id):
    game_store.add(TRUST_GAME)


@pytest.fixture
def trust_game() -> Game:
    """Return the Trust Game for testing."""
    return TRUST_GAME


@pytest.fixture
def client() -> TestClient:
    """Return FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def clean_store():
    """Fixture that ensures a clean game store for testing."""
    # Store original games
    original_games = {g.id: g for g in [game_store.get(s.id) for s in game_store.list()]}

    yield game_store

    # Restore original state
    current_ids = {s.id for s in game_store.list()}
    for game_id in current_ids:
        if game_id not in original_games:
            game_store.remove(game_id)
    for game_id, game in original_games.items():
        if game_id not in current_ids and game is not None:
            game_store.add(game)
