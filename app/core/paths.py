"""Path utilities for robust project root discovery.

Uses sentinel file lookup instead of fragile relative path navigation.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

# Sentinel files that indicate project root (in order of preference)
SENTINEL_FILES = ("pyproject.toml", "plugins.toml", ".git")


@lru_cache(maxsize=1)
def get_project_root() -> Path:
    """Find the project root by looking for sentinel files.

    Searches upward from the current file's location until it finds
    a directory containing one of the sentinel files.

    Returns:
        Path to the project root directory.

    Raises:
        RuntimeError: If no project root can be found.
    """
    # Start from this file's directory
    current = Path(__file__).resolve().parent

    # Search up to 10 levels (reasonable limit to avoid infinite loops)
    for _ in range(10):
        for sentinel in SENTINEL_FILES:
            if (current / sentinel).exists():
                return current
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            break
        current = parent

    # Fallback to the traditional relative path approach
    # This allows the code to work even if sentinel files are missing
    fallback = Path(__file__).resolve().parent.parent.parent
    if fallback.exists():
        return fallback

    raise RuntimeError(
        f"Could not find project root. Searched for sentinel files: {SENTINEL_FILES}"
    )


def get_examples_dir() -> Path:
    """Get the examples directory path."""
    return get_project_root() / "examples"


def get_plugins_config() -> Path:
    """Get the plugins.toml configuration file path."""
    return get_project_root() / "plugins.toml"
