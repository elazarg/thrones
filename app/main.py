from __future__ import annotations

import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.store import game_store
from app.formats import parse_game, supported_formats
from app.static_mount import mount_frontend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Import plugins for registration side effects
from app.plugins import discover_plugins


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize app state on startup."""
    logger.info("Starting Game Theory Workbench...")
    discover_plugins()
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

# Routers
from app.routes.games import router as games_router
from app.routes.analyses import router as analyses_router
from app.routes.tasks import router as tasks_router

app.include_router(games_router)
app.include_router(analyses_router)
app.include_router(tasks_router)

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

mount_frontend(app)
