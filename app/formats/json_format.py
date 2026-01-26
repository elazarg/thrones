"""Native JSON format parser and serializer.

Parses/serializes games in our native Pydantic model format.
Supports both extensive form (Game) and normal form (NormalFormGame).
"""
from __future__ import annotations

import json
import uuid
from typing import Union

from app.formats import register_format
from app.models.game import ExtensiveFormGame
from app.models.normal_form import NormalFormGame

AnyGame = Union[ExtensiveFormGame, NormalFormGame]


def parse_json(content: str, filename: str = "game.json") -> AnyGame:
    """Parse JSON format into ExtensiveFormGame or NormalFormGame model.

    Detects format by presence of 'strategies' key (normal form)
    vs 'nodes' key (extensive form).
    """
    data = json.loads(content)

    # Ensure ID exists
    if "id" not in data:
        data["id"] = str(uuid.uuid4())

    # Detect format: normal form has 'strategies', extensive form has 'nodes'
    if "strategies" in data:
        return NormalFormGame.model_validate(data)
    return ExtensiveFormGame.model_validate(data)


def serialize_json(game: AnyGame) -> str:
    """Serialize Game or NormalFormGame model to JSON."""
    return game.model_dump_json(indent=2)


# Register format
register_format(".json", parse_json, serialize_json)
