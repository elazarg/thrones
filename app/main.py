from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.registry import AnalysisResult, registry
from app.core.store import GameSummary, game_store
from app.formats import parse_game, supported_formats
from app.models.game import Action, DecisionNode, Game, Outcome

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


# Default Trust Game for backwards compatibility and demo
TRUST_GAME = Game(
    id="trust-game",
    title="Trust Game",
    players=["Alice", "Bob"],
    root="n_start",
    nodes={
        "n_start": DecisionNode(
            id="n_start",
            player="Alice",
            actions=[
                Action(label="Trust", target="n_bob"),
                Action(label="Don't", target="o_decline"),
            ],
        ),
        "n_bob": DecisionNode(
            id="n_bob",
            player="Bob",
            actions=[
                Action(label="Honor", target="o_coop"),
                Action(label="Betray", target="o_betray", warning="Dominated by Honor"),
            ],
        ),
    },
    outcomes={
        "o_coop": Outcome(label="Cooperate", payoffs={"Alice": 1, "Bob": 1}),
        "o_betray": Outcome(label="Betray", payoffs={"Alice": -1, "Bob": 2}),
        "o_decline": Outcome(label="Decline", payoffs={"Alice": 0, "Bob": 0}),
    },
    version="v1",
    tags=["sequential", "2-player", "example"],
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
    # Add default Trust Game
    game_store.add(TRUST_GAME)
    logger.info("Loaded default Trust Game")
    # Load example games
    _load_example_games()
    logger.info(f"Ready. {len(game_store.list())} games loaded.")


# =============================================================================
# Game Management API
# =============================================================================


@app.get("/api/games", response_model=list[GameSummary])
def list_games() -> list[GameSummary]:
    """List all loaded games."""
    return game_store.list()


@app.get("/api/games/{game_id}", response_model=Game)
def get_game(game_id: str) -> Game:
    """Get a specific game by ID."""
    game = game_store.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")
    return game


@app.delete("/api/games/{game_id}")
def delete_game(game_id: str) -> dict:
    """Delete a game."""
    if not game_store.remove(game_id):
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")
    return {"status": "deleted", "id": game_id}


@app.post("/api/games/upload", response_model=Game)
async def upload_game(file: UploadFile) -> Game:
    """Upload and parse a game file (.efg, .nfg, .json)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    logger.info(f"Uploading game: {file.filename}")
    try:
        content = await file.read()
        content_str = content.decode("utf-8")
        game = parse_game(content_str, file.filename)
        game_store.add(game)
        logger.info(f"Uploaded game: {game.title} ({game.id})")
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
                result = plugin.run(game)
                results.append(result)
                logger.info(f"Analysis complete: {plugin.name}")
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
    """Reset all state - clear all loaded games."""
    count = len(game_store.list())
    game_store.clear()
    # Re-add default Trust Game
    game_store.add(TRUST_GAME)
    logger.info(f"Reset state. Cleared {count} games, restored Trust Game.")
    return {"status": "reset", "games_cleared": count}


# Legacy endpoints for backwards compatibility
@app.get("/api/game", response_model=Game, deprecated=True)
def get_default_game() -> Game:
    """Get the default Trust Game. Deprecated: use /api/games/{id} instead."""
    return TRUST_GAME


@app.get("/api/analyses", response_model=list[AnalysisResult], deprecated=True)
def run_default_analyses() -> list[AnalysisResult]:
    """Run analyses on default game. Deprecated: use /api/games/{id}/analyses."""
    return [
        plugin.run(TRUST_GAME)
        for plugin in registry.analyses()
        if plugin.continuous and plugin.can_run(TRUST_GAME)
    ]


# =============================================================================
# Static Files (must be last - catch-all)
# =============================================================================

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
dist_dir = frontend_dir / "dist"

# Prefer built assets if they exist, otherwise fall back to source
static_dir = dist_dir if dist_dir.exists() else frontend_dir
app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
