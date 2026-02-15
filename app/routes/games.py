from __future__ import annotations

import logging

from fastapi import APIRouter, UploadFile
from starlette.concurrency import run_in_threadpool

from app.config import MAX_UPLOAD_SIZE_BYTES
from app.core.errors import (
    bad_request,
    conversion_failed,
    invalid_format,
    not_found,
    parse_failed,
)
from app.core.store import AnyGame, GameSummary, is_supported_format
from app.dependencies import GameStoreDep
from app.formats import parse_game

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["games"])


@router.get("/games", response_model=list[GameSummary])
def list_games(store: GameStoreDep) -> list[GameSummary]:
    """List all loaded games."""
    return store.list()


@router.get("/games/{game_id}")
def get_game(game_id: str, store: GameStoreDep) -> AnyGame:
    """Get a specific game by ID.

    Returns either Game (extensive form) or NormalFormGame (strategic form)
    depending on how the game was loaded.
    """
    game = store.get(game_id)
    if game is None:
        raise not_found("Game", game_id)
    return game


@router.get("/games/{game_id}/summary", response_model=GameSummary)
def get_game_summary(game_id: str, store: GameStoreDep) -> GameSummary:
    """Get game summary with conversion info.

    Use this to get conversion availability for a specific game.
    More expensive than the list endpoint but provides full conversion details.
    """
    summary = store.get_summary(game_id)
    if summary is None:
        raise not_found("Game", game_id)
    return summary


@router.get("/games/{game_id}/as/{target_format}")
def get_game_as_format(game_id: str, target_format: str, store: GameStoreDep) -> AnyGame:
    """Get a game converted to a specific format.

    Args:
        game_id: The game ID
        target_format: Target format - "extensive" or "normal"

    Returns the game in the requested format (converted if needed, cached).
    """
    if not is_supported_format(target_format):
        raise bad_request(f"Invalid format: {target_format}")

    game = store.get(game_id)
    if game is None:
        raise not_found("Game", game_id)

    converted = store.get_converted(game_id, target_format)
    if converted is None:
        raise conversion_failed(game.format_name, target_format)

    return converted


@router.delete("/games/{game_id}")
def delete_game(game_id: str, store: GameStoreDep) -> dict:
    """Delete a game."""
    if not store.remove(game_id):
        raise not_found("Game", game_id)
    return {"status": "deleted", "id": game_id}


def _truncate_error_message(message: str, max_length: int = 200) -> str:
    """Truncate error message to avoid leaking excessive internal details."""
    if len(message) <= max_length:
        return message
    return message[:max_length] + "..."


@router.post("/games/upload")
async def upload_game(file: UploadFile, store: GameStoreDep) -> AnyGame:
    """Upload and parse a game file (.efg, .nfg, .json).

    Returns Game or NormalFormGame depending on file type.
    """
    if not file.filename:
        raise bad_request("No filename provided")

    # Check file size before reading entire content into memory
    # This prevents OOM attacks from extremely large uploads
    if file.size is not None and file.size > MAX_UPLOAD_SIZE_BYTES:
        max_mb = MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
        raise bad_request(f"File too large. Maximum size is {max_mb:.1f}MB")

    logger.info("Uploading game: %s", file.filename)
    try:
        content = await file.read()
        # Double-check actual content size (file.size may not always be available)
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            max_mb = MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
            raise bad_request(f"File too large. Maximum size is {max_mb:.1f}MB")
        content_str = content.decode("utf-8")
        # Offload CPU-bound parsing to thread pool to avoid blocking the event loop
        game = await run_in_threadpool(parse_game, content_str, file.filename)
        store.add(game)
        fmt = game.format_name
        logger.info("Uploaded game: %s (%s) [%s]", game.title, game.id, fmt)
        return game
    except ValueError as e:
        logger.error("Upload failed (invalid format): %s", e)
        # Include truncated error message for actionable feedback
        error_msg = _truncate_error_message(str(e))
        raise invalid_format(file.filename, error_msg) from e
    except Exception as e:
        logger.error("Upload failed: %s", e)
        raise parse_failed() from e
