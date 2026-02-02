"""Remote format parsing via plugin services.

Proxies format parsing requests to remote plugin services that support
specific file formats (e.g., .efg, .nfg via the gambit plugin).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.config import RemoteFormatConfig
from app.core.http_client import RemoteServiceClient, RemoteServiceError

if TYPE_CHECKING:
    from app.models import AnyGame

logger = logging.getLogger(__name__)


def create_remote_parser(plugin_url: str, format_ext: str, plugin_name: str = "gambit"):
    """Create a parser function that proxies to a remote plugin.

    Args:
        plugin_url: Base URL of the plugin service (e.g., "http://127.0.0.1:5001")
        format_ext: File extension including dot (e.g., ".efg")
        plugin_name: Name of the plugin for error messages

    Returns:
        A parser function with signature (content: str, filename: str) -> AnyGame
    """
    endpoint = format_ext.lstrip(".")  # ".efg" -> "efg"
    client = RemoteServiceClient(plugin_url, service_name=plugin_name)

    def parse_via_plugin(content: str, filename: str = "") -> AnyGame:
        """Parse game file using remote plugin."""
        from app.models.extensive_form import ExtensiveFormGame
        from app.models.maid import MAIDGame
        from app.models.normal_form import NormalFormGame
        from app.models.vegas import VegasGame

        if not filename:
            filename = f"game{format_ext}"

        logger.debug("Parsing %s via %s/parse/%s", filename, plugin_url, endpoint)

        try:
            response = client.post(
                f"/parse/{endpoint}",
                json={"content": content, "filename": filename},
                timeout=RemoteFormatConfig.PARSE_TIMEOUT_SECONDS,
            )
        except RemoteServiceError as e:
            if e.error.code == "UNREACHABLE":
                raise ValueError(
                    f"Cannot parse {format_ext} files: plugin service is unreachable. "
                    f"Ensure the {plugin_name} plugin is running."
                ) from e
            raise ValueError(f"Failed to parse {filename}: {e.error.message}") from e

        game_dict = response["game"]

        # Convert to appropriate model based on format_name
        format_name = game_dict.get("format_name", "extensive")
        if format_name == "normal":
            return NormalFormGame(**game_dict)
        if format_name == "maid":
            return MAIDGame(**game_dict)
        if format_name == "vegas":
            return VegasGame(**game_dict)
        return ExtensiveFormGame(**game_dict)

    return parse_via_plugin
