"""Native JSON format parser and serializer.

Parses/serializes games in our native Pydantic model format.
"""
from __future__ import annotations

import json
import uuid

from app.formats import register_format
from app.models.game import Game


def parse_json(content: str, filename: str = "game.json") -> Game:
    """Parse JSON format into Game model."""
    data = json.loads(content)

    # Ensure ID exists
    if "id" not in data:
        data["id"] = str(uuid.uuid4())

    return Game.model_validate(data)


def serialize_json(game: Game) -> str:
    """Serialize Game model to JSON."""
    return game.model_dump_json(indent=2)


# Register format
register_format(".json", parse_json, serialize_json)
