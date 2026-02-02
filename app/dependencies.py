"""FastAPI dependency injection factories and shared type aliases.

Provides factory functions for core services that can be injected into route
handlers using FastAPI's Depends() pattern. This allows:

1. Easier testing - dependencies can be overridden with mocks
2. Parallel test execution - tests can use isolated instances
3. Clearer dependencies - each route declares what it needs

Usage in routes:
    from app.dependencies import GameStoreDep, RegistryDep

    @router.get("/games")
    def list_games(store: GameStoreDep) -> list[GameSummary]:
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
from typing import Annotated

from fastapi import Depends


@lru_cache(maxsize=1)
def get_game_store() -> GameStore:
    """Get the game store singleton."""
    from app.core.store import GameStore

    return GameStore()


@lru_cache(maxsize=1)
def get_task_manager() -> TaskManager:
    """Get the task manager singleton."""
    from app.core.tasks import TaskManager

    return TaskManager()


@lru_cache(maxsize=1)
def get_registry() -> Registry:
    """Get the analysis plugin registry singleton."""
    from app.core.registry import Registry

    return Registry()


@lru_cache(maxsize=1)
def get_conversion_registry() -> ConversionRegistry:
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


# =============================================================================
# Type aliases for dependency injection
# =============================================================================
# These provide cleaner route signatures by combining the type with Depends().
# Import these directly in route files instead of defining locally.
#
# Usage:
#   from app.dependencies import GameStoreDep, RegistryDep
#
#   @router.get("/games")
#   def list_games(store: GameStoreDep) -> list[GameSummary]:
#       return store.list()

# Import actual types - safe because core modules don't import from dependencies
from app.conversions.registry import ConversionRegistry  # noqa: E402
from app.core.registry import Registry  # noqa: E402
from app.core.store import GameStore  # noqa: E402
from app.core.tasks import TaskManager  # noqa: E402

GameStoreDep = Annotated[GameStore, Depends(get_game_store)]
TaskManagerDep = Annotated[TaskManager, Depends(get_task_manager)]
RegistryDep = Annotated[Registry, Depends(get_registry)]
ConversionRegistryDep = Annotated[ConversionRegistry, Depends(get_conversion_registry)]
