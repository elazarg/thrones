"""Native JSON format parser and serializer.

Parses/serializes games in our native Pydantic model format.
Supports ExtensiveFormGame, NormalFormGame, and MAIDGame.
"""
from __future__ import annotations

import json
import uuid

from app.formats import register_format
from app.models import AnyGame, ExtensiveFormGame, MAIDGame, NormalFormGame


def _is_maid_format(data: dict) -> bool:
    """Detect if JSON data represents a MAID game.

    A MAID is detected by:
    - format_name == "maid", or
    - nodes list where nodes have a 'type' field with decision/utility/chance
    """
    if data.get("format_name") == "maid":
        return True

    nodes = data.get("nodes", [])
    if nodes and isinstance(nodes, list):
        # Check if nodes have MAID-style type field
        first_node = nodes[0] if nodes else {}
        if isinstance(first_node, dict) and first_node.get("type") in ("decision", "utility", "chance"):
            return True

    return False


def parse_json(content: str, filename: str = "game.json") -> AnyGame:
    """Parse JSON format into ExtensiveFormGame, NormalFormGame, or MAIDGame.

    Detects format by:
    - 'format_name' field if present
    - 'strategies' key indicates normal form
    - 'nodes' with 'type' field indicates MAID
    - Otherwise defaults to extensive form
    """
    data = json.loads(content)

    # Ensure ID exists
    if "id" not in data:
        data["id"] = str(uuid.uuid4())

    # Detect format
    if _is_maid_format(data):
        return MAIDGame.model_validate(data)
    if "strategies" in data:
        return NormalFormGame.model_validate(data)
    return ExtensiveFormGame.model_validate(data)


def serialize_json(game: AnyGame) -> str:
    """Serialize Game or NormalFormGame model to JSON."""
    return game.model_dump_json(indent=2)


# Register format
register_format(".json", parse_json, serialize_json)
