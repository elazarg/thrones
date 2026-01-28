from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bootstrap import load_example_games
from app.core.paths import get_project_root
from app.core.store import game_store
from app.static_mount import mount_frontend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Import plugins for registration side effects
from app.plugins import discover_plugins, start_remote_plugins, stop_remote_plugins


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize app state on startup."""
    logger.info("Starting Game Theory Workbench...")
    discover_plugins()

    # Start remote plugin services (subprocess-managed)
    project_root = get_project_root()
    remote_results = start_remote_plugins(project_root)
    for name, ok in remote_results.items():
        if ok:
            logger.info("Remote plugin started: %s", name)
        else:
            logger.warning("Remote plugin failed to start: %s", name)

    load_example_games()
    logger.info("Ready. %d games loaded.", len(game_store.list()))
    yield

    # Shutdown remote plugins
    stop_remote_plugins()


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
    load_example_games()
    logger.info("Reset state. Cleared %d games, restored %d examples.", count, len(game_store.list()))
    return {"status": "reset", "games_cleared": count}

mount_frontend(app)
