from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bootstrap import load_example_games
from app.core.paths import get_project_root
from app.dependencies import get_game_store
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
    store = get_game_store()
    logger.info("Ready. %d games loaded.", len(store.list()))
    yield

    # Shutdown store's background executor
    store.shutdown(wait=True)

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
    store = get_game_store()
    return {
        "status": "ok",
        "games_loaded": len(store.list()),
    }


@app.post("/api/reset")
def reset_state() -> dict:
    """Reset all state - clear all loaded games and reload examples."""
    store = get_game_store()
    count = len(store.list())
    store.clear()
    load_example_games()
    logger.info("Reset state. Cleared %d games, restored %d examples.", count, len(store.list()))
    return {"status": "reset", "games_cleared": count}


@app.get("/api/plugins/status")
def get_plugin_status() -> list[dict]:
    """Return status of all managed plugins."""
    from app.plugins import plugin_manager

    statuses = []
    for name, pp in plugin_manager.plugins.items():
        status: dict = {
            "name": name,
            "healthy": pp.healthy,
            "port": pp.port if pp.healthy else None,
            "analyses": [a.get("name") for a in pp.analyses] if pp.healthy else [],
        }
        # Include compile_targets if the plugin advertises them
        if pp.healthy and pp.info.get("compile_targets"):
            status["compile_targets"] = pp.info["compile_targets"]
        statuses.append(status)
    return statuses


@app.post("/api/compile/{plugin_name}/{target}")
def compile_game(plugin_name: str, target: str, request: dict) -> dict:
    """Proxy compile request to a plugin.

    Request body should contain: { source_code: str, filename?: str }
    """
    from app.plugins import plugin_manager

    pp = plugin_manager.get_plugin(plugin_name)
    if pp is None or not pp.healthy:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found or unhealthy")

    # Forward request to plugin
    import httpx
    try:
        resp = httpx.post(
            f"{pp.url}/compile/{target}",
            json=request,
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        from fastapi import HTTPException
        detail = e.response.json() if e.response.content else str(e)
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=502, detail=f"Plugin communication error: {e}")


mount_frontend(app)
