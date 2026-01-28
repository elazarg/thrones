"""FastAPI dependency injection factories.

Provides factory functions for core services that can be injected into route
handlers using FastAPI's Depends() pattern. This allows:

1. Easier testing - dependencies can be overridden with mocks
2. Parallel test execution - tests can use isolated instances
3. Clearer dependencies - each route declares what it needs

Usage in routes:
    from fastapi import Depends
    from app.dependencies import get_game_store

    @router.get("/games")
    def list_games(store: GameStore = Depends(get_game_store)):
        return store.list()

Usage in tests:
    from app.dependencies import get_game_store

    def test_list_games():
        mock_store = Mock(spec=GameStore)
        app.dependency_overrides[get_game_store] = lambda: mock_store
        # ... test ...
        app.dependency_overrides.clear()
"""
from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.store import GameStore
    from app.core.tasks import TaskManager
    from app.core.registry import Registry
    from app.conversions.registry import ConversionRegistry


@lru_cache(maxsize=1)
def get_game_store() -> "GameStore":
    """Get the game store singleton."""
    from app.core.store import GameStore
    return GameStore()


@lru_cache(maxsize=1)
def get_task_manager() -> "TaskManager":
    """Get the task manager singleton."""
    from app.core.tasks import TaskManager
    return TaskManager()


@lru_cache(maxsize=1)
def get_registry() -> "Registry":
    """Get the analysis plugin registry singleton."""
    from app.core.registry import Registry
    return Registry()


@lru_cache(maxsize=1)
def get_conversion_registry() -> "ConversionRegistry":
    """Get the conversion registry singleton."""
    from app.conversions.registry import ConversionRegistry
    return ConversionRegistry()


def reset_dependencies() -> None:
    """Reset all cached dependencies.

    Call this in test fixtures to ensure fresh instances between tests.
    """
    get_game_store.cache_clear()
    get_task_manager.cache_clear()
    get_registry.cache_clear()
    get_conversion_registry.cache_clear()
