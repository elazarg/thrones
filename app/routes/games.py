from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, UploadFile
from app.core.store import AnyGame, GameSummary, game_store
from app.models.normal_form import NormalFormGame
from app.formats import parse_game

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["games"])

@router.get("/games", response_model=list[GameSummary])
def list_games() -> list[GameSummary]:
    """List all loaded games."""
    return game_store.list()


@router.get("/games/{game_id}")
def get_game(game_id: str) -> AnyGame:
    """Get a specific game by ID.

    Returns either Game (extensive form) or NormalFormGame (strategic form)
    depending on how the game was loaded.
    """
    game = game_store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")
    return game


@router.get("/games/{game_id}/as/{target_format}")
def get_game_as_format(game_id: str, target_format: str) -> AnyGame:
    """Get a game converted to a specific format.

    Args:
        game_id: The game ID
        target_format: Target format - "extensive" or "normal"

    Returns the game in the requested format (converted if needed, cached).
    """
    if target_format not in ("extensive", "normal"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format: {target_format}. Must be 'extensive' or 'normal'",
        )

    game = game_store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")

    converted = game_store.get_converted(game_id, target_format)
    if converted is None:
        current_format = "normal" if isinstance(game, NormalFormGame) else "extensive"
        raise HTTPException(
            status_code=400,
            detail=f"Cannot convert from {current_format} to {target_format}",
        )

    return converted


@router.delete("/games/{game_id}")
def delete_game(game_id: str) -> dict:
    """Delete a game."""
    if not game_store.remove(game_id):
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")
    return {"status": "deleted", "id": game_id}


@router.post("/games/upload")
async def upload_game(file: UploadFile) -> AnyGame:
    """Upload and parse a game file (.efg, .nfg, .json).

    Returns Game or NormalFormGame depending on file type.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    logger.info(f"Uploading game: {file.filename}")
    try:
        content = await file.read()
        content_str = content.decode("utf-8")
        game = parse_game(content_str, file.filename)
        game_store.add(game)
        fmt = "normal" if isinstance(game, NormalFormGame) else "extensive"
        logger.info(f"Uploaded game: {game.title} ({game.id}) [{fmt}]")
        return game
    except ValueError as e:
        logger.error(f"Upload failed (invalid format): {e}")
        # Sanitize error message - only include the error type and safe message
        raise HTTPException(status_code=400, detail=f"Invalid game format: {type(e).__name__}")
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        # Don't leak internal details in error response
        raise HTTPException(status_code=500, detail="Failed to parse game file")

