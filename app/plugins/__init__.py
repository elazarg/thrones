"""Plugin package with auto-discovery hooks."""
from __future__ import annotations

import importlib
import pkgutil
import logging
from pathlib import Path

from app.core.plugin_manager import PluginManager
from app.core.remote_plugin import RemotePlugin
from app.core.registry import registry

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
        logger.info(f"Discovered plugin module: {module_info.name}")
        discovered.append(module_info.name)

    return tuple(discovered)


def start_remote_plugins(project_root: Path | None = None) -> dict[str, bool]:
    """Load config, start remote plugin subprocesses, register their analyses.

    Returns {plugin_name: started_ok}.
    """
    from app.formats import register_format
    from app.formats.remote import create_remote_parser
    from app.conversions.registry import conversion_registry
    from app.conversions.remote import create_remote_conversion

    plugin_manager.load_config(project_root)
    results = plugin_manager.start_all()

    # Register RemotePlugin adapters for each healthy plugin's analyses
    for pp in plugin_manager.healthy_plugins():
        for analysis_info in pp.analyses:
            remote = RemotePlugin(base_url=pp.url, analysis_info=analysis_info)
            registry.register_analysis(remote)
            logger.info(
                "Registered remote analysis: %s (from %s at %s)",
                remote.name, pp.config.name, pp.url,
            )

        # Register format parsers from plugins
        for fmt in pp.info.get("formats", []):
            parser = create_remote_parser(pp.url, fmt)
            register_format(fmt, parser, None)
            logger.info(
                "Registered remote format: %s from %s",
                fmt, pp.config.name,
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
                conv["source"], conv["target"], pp.config.name, pp.url,
            )

    return results


def stop_remote_plugins() -> None:
    """Stop all managed remote plugin subprocesses."""
    plugin_manager.stop_all()
