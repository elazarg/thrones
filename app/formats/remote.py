"""Remote format parsing via plugin services.

Proxies format parsing requests to remote plugin services that support
specific file formats (e.g., .efg, .nfg via the gambit plugin).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from app.models import AnyGame

logger = logging.getLogger(__name__)


def create_remote_parser(plugin_url: str, format_ext: str):
    """Create a parser function that proxies to a remote plugin.

    Args:
        plugin_url: Base URL of the plugin service (e.g., "http://127.0.0.1:5001")
        format_ext: File extension including dot (e.g., ".efg")

    Returns:
        A parser function with signature (content: str, filename: str) -> AnyGame
    """
    endpoint = format_ext.lstrip(".")  # ".efg" -> "efg"

    def parse_via_plugin(content: str, filename: str = "") -> "AnyGame":
        """Parse game file using remote plugin."""
        from app.models.extensive_form import ExtensiveFormGame
        from app.models.normal_form import NormalFormGame

        if not filename:
            filename = f"game{format_ext}"

        url = f"{plugin_url}/parse/{endpoint}"
        logger.debug("Parsing %s via %s", filename, url)

        try:
            resp = httpx.post(
                url,
                json={"content": content, "filename": filename},
                timeout=30.0,
            )
            resp.raise_for_status()
        except httpx.ConnectError:
            raise ValueError(
                f"Cannot parse {format_ext} files: plugin service is unreachable. "
                f"Ensure the gambit plugin is running."
            )
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", {})
            error = detail.get("error", {})
            msg = error.get("message", str(e))
            raise ValueError(f"Failed to parse {filename}: {msg}")

        game_dict = resp.json()["game"]

        # Convert to appropriate model based on format_name
        format_name = game_dict.get("format_name", "extensive")
        if format_name == "normal":
            return NormalFormGame(**game_dict)
        return ExtensiveFormGame(**game_dict)

    return parse_via_plugin
