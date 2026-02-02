"""Remote conversion via plugin services.

Proxies conversion requests to remote plugin services that support
game format conversions (e.g., MAID to EFG via the pycid plugin).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.config import RemoteFormatConfig
from app.conversions.registry import Conversion, ConversionCheck
from app.core.http_client import RemoteServiceClient, RemoteServiceError

if TYPE_CHECKING:
    from app.models import AnyGame

logger = logging.getLogger(__name__)


def create_remote_conversion(
    plugin_url: str,
    source_format: str,
    target_format: str,
    plugin_name: str = "remote",
) -> Conversion:
    """Create a Conversion that delegates to a remote plugin.

    Args:
        plugin_url: Base URL of the plugin service (e.g., "http://127.0.0.1:5002")
        source_format: Source format name (e.g., "maid")
        target_format: Target format name (e.g., "extensive")
        plugin_name: Name of the plugin for display purposes

    Returns:
        A Conversion object that proxies to the remote plugin.
    """
    client = RemoteServiceClient(plugin_url, service_name=plugin_name)

    def can_convert(game: AnyGame) -> ConversionCheck:
        """Check if this game can be converted."""
        if game.format_name != source_format:
            return ConversionCheck(
                possible=False,
                blockers=[f"Game format '{game.format_name}' is not '{source_format}'"],
            )
        return ConversionCheck(possible=True)

    def convert(game: AnyGame) -> AnyGame:
        """Convert the game via remote plugin."""
        from app.models.extensive_form import ExtensiveFormGame
        from app.models.maid import MAIDGame
        from app.models.normal_form import NormalFormGame

        endpoint = f"/convert/{source_format}-to-{target_format}"
        logger.debug("Converting via %s%s", plugin_url, endpoint)

        try:
            response = client.post(
                endpoint,
                json={"game": game.model_dump()},
                timeout=RemoteFormatConfig.CONVERT_TIMEOUT_SECONDS,
            )
        except RemoteServiceError as e:
            if e.error.code == "UNREACHABLE":
                raise ValueError(
                    f"Cannot convert {source_format} to {target_format}: "
                    f"plugin service is unreachable. Ensure the {plugin_name} plugin is running."
                ) from e
            raise ValueError(f"Conversion failed: {e.error.message}") from e

        game_dict = response.get("game")
        if not game_dict:
            raise ValueError("Conversion response missing 'game' field")

        # Convert to appropriate model based on format_name
        format_name = game_dict.get("format_name", target_format)
        try:
            if format_name == "normal":
                return NormalFormGame(**game_dict)
            elif format_name == "maid":
                return MAIDGame(**game_dict)
            return ExtensiveFormGame(**game_dict)
        except Exception as e:
            raise ValueError(f"Failed to parse converted game: {e}") from e

    return Conversion(
        name=f"{source_format} to {target_format} (via {plugin_name})",
        source_format=source_format,
        target_format=target_format,
        can_convert=can_convert,
        convert=convert,
    )
