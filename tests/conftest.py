"""Shared test fixtures for Game Theory Workbench."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import TRUST_GAME, app
from app.models.game import Game


@pytest.fixture
def trust_game() -> Game:
    """Return the Trust Game for testing."""
    return TRUST_GAME


@pytest.fixture
def client() -> TestClient:
    """Return FastAPI test client."""
    return TestClient(app)
