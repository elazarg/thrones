"""Plugin package with auto-discovery hooks."""

from __future__ import annotations

import importlib
import logging
import pkgutil
import threading
from pathlib import Path

from app.core.plugin_manager import PluginManager
from app.core.remote_plugin import RemotePlugin
from app.dependencies import get_registry, get_conversion_registry

logger = logging.getLogger(__name__)

# Global plugin manager for remote plugins
plugin_manager = PluginManager()


def discover_plugins() -> tuple[str, ...]:
    """Import all local plugin modules under ``app.plugins`` for registration side-effects."""

    discovered: list[str] = []
    for module_info in pkgutil.iter_modules(__path__, prefix=f"{__name__}."):
        # Skip sub-packages (like 'gambit', 'pycid') - they are handled separately
        if module_info.ispkg:
            continue
        importlib.import_module(module_info.name)
        logger.info("Discovered plugin module: %s", module_info.name)
        discovered.append(module_info.name)

    return tuple(discovered)


def _register_plugin(pp) -> None:
    """Register a single healthy plugin's analyses, formats, and conversions."""
    from app.formats import register_format
    from app.formats.remote import create_remote_parser
    from app.conversions.remote import create_remote_conversion

    registry = get_registry()
    conversion_registry = get_conversion_registry()

    for analysis_info in pp.analyses:
        remote = RemotePlugin(base_url=pp.url, analysis_info=analysis_info)
        registry.register_analysis(remote)
        logger.info(
            "Registered remote analysis: %s (from %s at %s)",
            remote.name,
            pp.config.name,
            pp.url,
        )

    # Register format parsers from plugins
    for fmt in pp.info.get("formats", []):
        parser = create_remote_parser(pp.url, fmt, plugin_name=pp.config.name)
        register_format(fmt, parser, None)
        logger.info(
            "Registered remote format: %s from %s",
            fmt,
            pp.config.name,
        )

    # Register conversions from plugins
    for conv in pp.info.get("conversions", []):
        remote_conv = create_remote_conversion(
            pp.url,
            conv["source"],
            conv["target"],
            plugin_name=pp.config.name,
        )
        conversion_registry.register(remote_conv)
        logger.info(
            "Registered remote conversion: %s to %s (from %s at %s)",
            conv["source"],
            conv["target"],
            pp.config.name,
            pp.url,
        )


def register_healthy_plugins() -> list[str]:
    """Register any healthy plugins that haven't been registered yet.

    Call this periodically or before plugin-dependent operations.
    Returns list of newly registered plugin names.
    """
    newly_registered = []

    for pp in plugin_manager.healthy_plugins():
        # Use plugin_manager's thread-safe registration tracking
        if plugin_manager.mark_registered(pp.config.name):
            _register_plugin(pp)
            newly_registered.append(pp.config.name)

    return newly_registered


def start_remote_plugins(
    project_root: Path | None = None, background: bool = False
) -> dict[str, bool]:
    """Discover Docker Compose-managed plugins and register their analyses.

    If background=True, discovers plugins in background and returns immediately.
    Call register_healthy_plugins() later to register analyses as plugins become ready.

    Returns {plugin_name: discovered_ok} (empty dict if background=True).
    """
    plugin_manager.load_config(project_root)

    if background:

        def _discover_and_register():
            plugin_manager.start_all(background=False)
            register_healthy_plugins()

        thread = threading.Thread(target=_discover_and_register, daemon=True)
        thread.start()
        return {}

    results = plugin_manager.start_all()
    register_healthy_plugins()
    return results


def stop_remote_plugins() -> None:
    """No-op: Docker Compose manages container lifecycle."""
    plugin_manager.stop_all()
