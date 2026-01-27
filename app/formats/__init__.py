"""Game format parsers and serializers.

Supports loading games from various file formats:
- .efg: Gambit extensive form (via gambit plugin)
- .nfg: Gambit normal form (via gambit plugin)
- .json: Native JSON format

Gambit formats (.efg, .nfg) are parsed by the remote gambit plugin and
registered dynamically on app startup when the plugin is healthy.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import AnyGame

# Format registry: extension -> (parser, serializer)
_FORMATS: dict[str, tuple] = {}


def register_format(
    extension: str,
    parser: callable,
    serializer: callable | None = None,
) -> None:
    """Register a format handler."""
    _FORMATS[extension.lower()] = (parser, serializer)


def load_game(path: str | Path) -> "AnyGame":
    """Load a game from a file path."""
    path = Path(path)
    ext = path.suffix.lower()

    if ext not in _FORMATS:
        supported = ", ".join(_FORMATS.keys())
        raise ValueError(f"Unsupported format: {ext}. Supported: {supported}")

    parser, _ = _FORMATS[ext]
    content = path.read_text(encoding="utf-8")
    return parser(content, filename=path.name)


def parse_game(content: str, filename: str) -> "AnyGame":
    """Parse game content, inferring format from filename."""
    ext = Path(filename).suffix.lower()

    if ext not in _FORMATS:
        supported = ", ".join(_FORMATS.keys())
        raise ValueError(f"Unsupported format: {ext}. Supported: {supported}")

    parser, _ = _FORMATS[ext]
    return parser(content, filename=filename)


def save_game(game: "AnyGame", path: str | Path, format: str | None = None) -> None:
    """Save a game to a file."""
    path = Path(path)
    ext = format or path.suffix.lower()

    if ext not in _FORMATS:
        supported = ", ".join(_FORMATS.keys())
        raise ValueError(f"Unsupported format: {ext}. Supported: {supported}")

    _, serializer = _FORMATS[ext]
    if serializer is None:
        raise ValueError(f"Format {ext} does not support serialization")

    content = serializer(game)
    path.write_text(content, encoding="utf-8")


def supported_formats() -> list[str]:
    """Return list of supported file extensions."""
    return list(_FORMATS.keys())


# Import format modules to trigger registration
# JSON format is always available
from app.formats import json_format  # noqa: E402, F401

# Gambit formats (.efg, .nfg) are registered dynamically by app.plugins
# when the gambit plugin starts and advertises format support.
