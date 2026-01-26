"""Plugin package with auto-discovery hooks."""
from __future__ import annotations

import importlib
import pkgutil
import logging

from app.core.dependencies import PYGAMBIT_AVAILABLE, PYCID_AVAILABLE

logger = logging.getLogger(__name__)


def discover_plugins() -> tuple[str, ...]:
    """Import all plugin modules under ``app.plugins`` for registration side-effects."""

    discovered: list[str] = []
    for module_info in pkgutil.iter_modules(__path__, prefix=f"{__name__}."):
        # Skip sub-packages (like 'gambit', 'pycid') - they are handled separately
        if module_info.ispkg:
            continue
        importlib.import_module(module_info.name)
        logger.info(f"Discovered plugin module: {module_info.name}")
        discovered.append(module_info.name)

    # Conditionally import gambit plugins if pygambit is available
    if PYGAMBIT_AVAILABLE:
        try:
            import app.plugins.gambit  # noqa: F401
            logger.info("Discovered gambit plugin package")
            discovered.append(f"{__name__}.gambit")
        except ImportError as e:
            logger.warning(f"Failed to import gambit plugins: {e}")

    # Conditionally import pycid plugins if pycid is available
    if PYCID_AVAILABLE:
        try:
            import app.plugins.pycid  # noqa: F401
            logger.info("Discovered pycid plugin package")
            discovered.append(f"{__name__}.pycid")
        except ImportError as e:
            logger.warning(f"Failed to import pycid plugins: {e}")

    return tuple(discovered)
