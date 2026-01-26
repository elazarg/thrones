"""Game format parsers and serializers.

Supports loading games from various file formats:
- .efg: Gambit extensive form (requires pygambit)
- .nfg: Gambit normal form (requires pygambit)
- .json: Native JSON format
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.core.dependencies import PYGAMBIT_AVAILABLE

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

# Gambit formats require pygambit
if PYGAMBIT_AVAILABLE:
    from app.formats import gambit  # noqa: E402, F401
