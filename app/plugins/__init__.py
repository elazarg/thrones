"""Plugin package with auto-discovery hooks."""
from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable
import logging

logger = logging.getLogger(__name__)

def discover_plugins() -> tuple[str, ...]:
    """Import all plugin modules under ``app.plugins`` for registration side-effects."""

    discovered: list[str] = []
    for module_info in pkgutil.iter_modules(__path__, prefix=f"{__name__}."):
        importlib.import_module(module_info.name)
        logger.info(f"Discovered plugin module: {module_info.name}")
        discovered.append(module_info.name)
    return tuple(discovered)
