from __future__ import annotations

import logging
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.registry import AnalysisResult, registry
from app.core.store import AnyGame, GameSummary, game_store
from app.core.tasks import task_manager, TaskStatus
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize app state on startup."""
    logger.info("Starting Game Theory Workbench...")
    _load_example_games()
    logger.info(f"Ready. {len(game_store.list())} games loaded.")
    yield


app = FastAPI(title="Game Theory Workbench", version="0.3.0", lifespan=lifespan)


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
        # Sanitize error message - only include the error type and safe message
        raise HTTPException(status_code=400, detail=f"Invalid game format: {type(e).__name__}")
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        # Don't leak internal details in error response
        raise HTTPException(status_code=500, detail="Failed to parse game file")


# =============================================================================
# Analysis API
# =============================================================================


@app.get("/api/games/{game_id}/analyses", response_model=list[AnalysisResult])
def run_game_analyses(
    game_id: str,
    solver: str | None = None,
    max_equilibria: int | None = None,
) -> list[AnalysisResult]:
    """Run continuous analyses on a specific game.

    Args:
        game_id: The game identifier
        solver: Nash solver type: 'exhaustive' (default), 'quick', or 'pure'
        max_equilibria: Max equilibria to find (for 'quick' solver)
    """
    game = game_store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")

    # Build config for plugins
    plugin_config: dict = {}
    if solver:
        plugin_config["solver"] = solver
    if max_equilibria:
        plugin_config["max_equilibria"] = max_equilibria

    logger.info(f"Running analyses for game: {game_id} (config={plugin_config})")
    results = []
    for plugin in registry.analyses():
        if plugin.continuous and plugin.can_run(game):
            try:
                start_time = time.perf_counter()
                result = plugin.run(game, config=plugin_config if plugin_config else None)
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
                # Sanitize error - include type but not potentially sensitive details
                results.append(AnalysisResult(
                    summary=f"{plugin.name}: error",
                    details={"error": f"Analysis failed: {type(e).__name__}"},
                ))
    return results


# =============================================================================
# Task API (Background Analysis)
# =============================================================================


@app.post("/api/tasks")
def submit_task(
    game_id: str,
    plugin: str,
    owner: str = "anonymous",
    solver: str | None = None,
    max_equilibria: int | None = None,
) -> dict:
    """Submit an analysis task for background execution.

    Args:
        game_id: The game to analyze.
        plugin: The analysis plugin name (e.g., "Nash").
        owner: Client identifier for task ownership.
        solver: Solver type for Nash plugin.
        max_equilibria: Max equilibria to find.

    Returns:
        Task info including task_id for polling.
    """
    # Validate game exists
    game = game_store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")

    # Find the plugin
    analysis_plugin = registry.get_analysis(plugin)
    if analysis_plugin is None:
        available = [p.name for p in registry.analyses()]
        raise HTTPException(
            status_code=400,
            detail=f"Unknown plugin: {plugin}. Available: {available}",
        )

    if not analysis_plugin.can_run(game):
        raise HTTPException(
            status_code=400,
            detail=f"Plugin '{plugin}' cannot run on this game",
        )

    # Build config
    config: dict = {}
    if solver:
        config["solver"] = solver
    if max_equilibria:
        config["max_equilibria"] = max_equilibria

    # Create a run function that captures the plugin and game
    def run_analysis(cfg: dict | None) -> dict:
        start_time = time.perf_counter()
        result = analysis_plugin.run(game, config=cfg)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "summary": result.summary,
            "details": {**result.details, "computation_time_ms": elapsed_ms},
        }

    # Submit to task manager
    task_id = task_manager.submit(
        owner=owner,
        game_id=game_id,
        plugin_name=plugin,
        run_fn=run_analysis,
        config=config if config else None,
    )

    logger.info(f"Task submitted: {task_id} ({plugin} on {game_id})")
    return {
        "task_id": task_id,
        "status": "pending",
        "plugin": plugin,
        "game_id": game_id,
    }


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    """Get task status and result.

    Args:
        task_id: The task identifier.

    Returns:
        Task info including status and result (if completed).
    """
    task = task_manager.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    return task.to_dict()


@app.delete("/api/tasks/{task_id}")
def cancel_task(task_id: str) -> dict:
    """Cancel a running task.

    Args:
        task_id: The task identifier.

    Returns:
        Cancellation status.
    """
    task = task_manager.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
        return {
            "task_id": task_id,
            "cancelled": False,
            "reason": f"Task already {task.status.value}",
        }

    success = task_manager.cancel(task_id)
    return {
        "task_id": task_id,
        "cancelled": success,
    }


@app.get("/api/tasks")
def list_tasks(owner: str | None = None) -> list[dict]:
    """List all tasks, optionally filtered by owner.

    Args:
        owner: Filter to tasks owned by this client.

    Returns:
        List of task info dictionaries.
    """
    tasks = task_manager.list_tasks(owner=owner)
    return [t.to_dict() for t in tasks]


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


# =============================================================================
# Static Files (must be last - catch-all)
# =============================================================================

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
dist_dir = frontend_dir / "dist"

# Prefer built assets if they exist, otherwise fall back to source
static_dir = dist_dir if dist_dir.exists() else frontend_dir
app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
