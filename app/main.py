from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.registry import AnalysisResult, registry
from app.core.store import AnyGame, GameSummary, game_store
from app.formats import parse_game, supported_formats
from app.models.game import Game
from app.models.normal_form import NormalFormGame

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Import plugins for registration side effects
from app.plugins import discover_plugins

discover_plugins()

app = FastAPI(title="Game Theory Workbench", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_example_games() -> None:
    """Load example games from examples/ directory."""
    examples_dir = Path(__file__).resolve().parent.parent / "examples"
    if not examples_dir.exists():
        return

    for ext in supported_formats():
        for file_path in examples_dir.glob(f"*{ext}"):
            try:
                content = file_path.read_text(encoding="utf-8")
                game = parse_game(content, file_path.name)
                game_store.add(game)
                logger.info(f"Loaded example: {file_path.name}")
            except Exception as e:
                logger.warning(f"Failed to load {file_path}: {e}")


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize app state on startup."""
    logger.info("Starting Game Theory Workbench...")
    _load_example_games()
    logger.info(f"Ready. {len(game_store.list())} games loaded.")


# =============================================================================
# Game Management API
# =============================================================================


@app.get("/api/games", response_model=list[GameSummary])
def list_games() -> list[GameSummary]:
    """List all loaded games."""
    return game_store.list()


@app.get("/api/games/{game_id}")
def get_game(game_id: str) -> AnyGame:
    """Get a specific game by ID.

    Returns either Game (extensive form) or NormalFormGame (strategic form)
    depending on how the game was loaded.
    """
    game = game_store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")
    return game


@app.get("/api/games/{game_id}/as/{target_format}")
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


@app.delete("/api/games/{game_id}")
def delete_game(game_id: str) -> dict:
    """Delete a game."""
    if not game_store.remove(game_id):
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")
    return {"status": "deleted", "id": game_id}


@app.post("/api/games/upload")
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse game: {e}")


# =============================================================================
# Analysis API
# =============================================================================


@app.get("/api/games/{game_id}/analyses", response_model=list[AnalysisResult])
def run_game_analyses(game_id: str) -> list[AnalysisResult]:
    """Run continuous analyses on a specific game."""
    game = game_store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")

    logger.info(f"Running analyses for game: {game_id}")
    results = []
    for plugin in registry.analyses():
        if plugin.continuous and plugin.can_run(game):
            try:
                start_time = time.perf_counter()
                result = plugin.run(game)
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)

                # Add timing to result details
                timed_result = AnalysisResult(
                    summary=result.summary,
                    details={**result.details, "computation_time_ms": elapsed_ms},
                )
                results.append(timed_result)
                logger.info(f"Analysis complete: {plugin.name} ({elapsed_ms}ms)")
            except Exception as e:
                logger.error(f"Analysis failed ({plugin.name}): {e}")
                results.append(AnalysisResult(
                    summary=f"{plugin.name}: error",
                    details={"error": str(e)},
                ))
    return results


# =============================================================================
# Utility API
# =============================================================================


@app.get("/api/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "games_loaded": len(game_store.list()),
    }


@app.post("/api/reset")
def reset_state() -> dict:
    """Reset all state - clear all loaded games and reload examples."""
    count = len(game_store.list())
    game_store.clear()
    _load_example_games()
    logger.info(f"Reset state. Cleared {count} games, restored {len(game_store.list())} examples.")
    return {"status": "reset", "games_cleared": count}


# Legacy endpoints for backwards compatibility
@app.get("/api/game", response_model=Game, deprecated=True)
def get_default_game() -> Game:
    """Get the default Trust Game. Deprecated: use /api/games/{id} instead."""
    game = game_store.get("trust-game")
    if game is None or not isinstance(game, Game):
        raise HTTPException(status_code=404, detail="Trust game not found")
    return game


@app.get("/api/analyses", response_model=list[AnalysisResult], deprecated=True)
def run_default_analyses() -> list[AnalysisResult]:
    """Run analyses on default game. Deprecated: use /api/games/{id}/analyses."""
    game = game_store.get("trust-game")
    if game is None:
        return []
    return [
        plugin.run(game)
        for plugin in registry.analyses()
        if plugin.continuous and plugin.can_run(game)
    ]


# =============================================================================
# Static Files (must be last - catch-all)
# =============================================================================

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
dist_dir = frontend_dir / "dist"

# Prefer built assets if they exist, otherwise fall back to source
static_dir = dist_dir if dist_dir.exists() else frontend_dir
app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
