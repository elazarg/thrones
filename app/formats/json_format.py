"""Native JSON format parser and serializer.

Parses/serializes games in our native Pydantic model format.
Supports ExtensiveFormGame, NormalFormGame, and MAIDGame.

The unified JSON format uses:
- Common fields: id, title, description, players, tags
- Format-specific data in exactly one of: game_efg, game_nfg, game_maid
"""

from __future__ import annotations

import json
import uuid

from app.formats import register_format
from app.models import AnyGame, ExtensiveFormGame, MAIDGame, NormalFormGame


def _transform_unified_format(data: dict) -> dict:
    """Transform unified JSON format to internal model format.

    Unified format has common fields + exactly one of game_efg/game_nfg/game_maid.
    Internal format has all fields at top level.
    """
    common = {
        "id": data.get("id"),
        "title": data.get("title"),
        "description": data.get("description"),
        "tags": data.get("tags", []),
    }

    if "game_efg" in data:
        game_data = data["game_efg"]
        return {
            **common,
            "players": data.get("players", []),
            "root": game_data.get("root"),
            "nodes": game_data.get("nodes", {}),
            "outcomes": game_data.get("outcomes", {}),
        }
    elif "game_nfg" in data:
        game_data = data["game_nfg"]
        return {
            **common,
            "players": data.get("players", []),
            "strategies": game_data.get("strategies", []),
            "payoffs": game_data.get("payoffs", []),
        }
    elif "game_maid" in data:
        game_data = data["game_maid"]
        return {
            **common,
            "agents": data.get("players", []),  # MAID uses 'agents' internally
            "nodes": game_data.get("nodes", []),
            "edges": game_data.get("edges", []),
            "cpds": game_data.get("cpds", []),
        }

    return data  # Not unified format, return as-is


def _is_unified_format(data: dict) -> bool:
    """Check if data uses the unified format."""
    return "game_efg" in data or "game_nfg" in data or "game_maid" in data


def _is_maid_format(data: dict) -> bool:
    """Detect if JSON data represents a MAID game (legacy format).

    A MAID is detected by:
    - format_name == "maid", or
    - 'agents' key present, or
    - nodes list where nodes have a 'type' field with decision/utility/chance
    """
    if data.get("format_name") == "maid":
        return True

    if "agents" in data:
        return True

    nodes = data.get("nodes", [])
    if nodes and isinstance(nodes, list):
        first_node = nodes[0] if nodes else {}
        if isinstance(first_node, dict) and first_node.get("type") in (
            "decision",
            "utility",
            "chance",
        ):
            return True

    return False


def parse_json(content: str, filename: str = "game.json") -> AnyGame:
    """Parse JSON format into ExtensiveFormGame, NormalFormGame, or MAIDGame.

    Supports both unified format (game_efg/game_nfg/game_maid) and legacy format.
    """
    data = json.loads(content)

    # Ensure ID exists
    if "id" not in data:
        data["id"] = str(uuid.uuid4())

    # Transform unified format to internal format
    if _is_unified_format(data):
        data = _transform_unified_format(data)

    # Detect and parse format
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
