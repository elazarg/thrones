from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import app.conversions  # Register format conversions (EFG <-> NFG, etc.)
from app.bootstrap import load_example_games
from app.config import CORS_ORIGINS, IS_PRODUCTION
from app.core.paths import get_project_root
from app.dependencies import get_conversion_registry, get_game_store
from app.plugins import (
    discover_plugins,
    plugin_manager,
    register_healthy_plugins,
    start_remote_plugins,
    stop_remote_plugins,
)
from app.static_mount import mount_frontend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class _HealthCheckFilter(logging.Filter):
    """Suppress successful health-check entries from uvicorn access log.

    Only hides 200 responses so failed health checks remain visible.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # uvicorn access log args: (client_addr, method, path, http_version, status_code)
        args = record.args
        if not isinstance(args, tuple) or len(args) < 5:
            return True
        path, status = args[2], args[4]
        return not (isinstance(path, str) and path.endswith("/health") and status == 200)


def _install_health_check_filter() -> None:
    """Add the filter to uvicorn's access logger and its handlers."""
    f = _HealthCheckFilter()
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.addFilter(f)
    for handler in access_logger.handlers:
        handler.addFilter(f)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize app state on startup."""
    _install_health_check_filter()
    logger.info("Starting Game Theory Workbench...")
    discover_plugins()

    # Discover remote plugin services in background (Docker Compose-managed)
    # This lets the server respond immediately while plugins are discovered
    project_root = get_project_root()
    start_remote_plugins(project_root, background=True)
    logger.info("Discovering plugins in background...")

    load_example_games()
    store = get_game_store()
    logger.info("Server ready. %d games loaded. Discovering plugins...", len(store.list()))
    yield

    # Shutdown store's background executor
    store.shutdown(wait=True)

    # Cleanup (no-op for Docker-managed plugins)
    stop_remote_plugins()


app = FastAPI(title="Game Theory Workbench", version="0.3.0", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers (imported after app initialization to avoid circular imports)
from app.routes.analyses import router as analyses_router  # noqa: E402
from app.routes.games import router as games_router  # noqa: E402
from app.routes.tasks import router as tasks_router  # noqa: E402

app.include_router(games_router)
app.include_router(analyses_router)
app.include_router(tasks_router)

# =============================================================================
# Utility API
# =============================================================================


@app.get("/api/health")
def health_check() -> dict:
    """Health check endpoint with plugin loading status."""

    # Register any newly-ready plugins
    register_healthy_plugins()

    store = get_game_store()
    loading = plugin_manager.loading_status

    if loading["loading"]:
        # Still initializing plugins
        progress_pct = int(loading["progress"] * 100)
        loading_names = loading["plugins_loading"]

        return {
            "status": "loading",
            "message": f"Initializing plugins... {progress_pct}%",
            "games_loaded": len(store.list()),
            "plugins": {
                "ready": loading["plugins_ready"],
                "total": loading["total_plugins"],
                "loading": loading_names,
            },
        }

    # All plugins initialized
    healthy = plugin_manager.healthy_plugins()
    return {
        "status": "ok",
        "games_loaded": len(store.list()),
        "plugins_healthy": len(healthy),
    }


if not IS_PRODUCTION:

    @app.post("/api/reset")
    def reset_state() -> dict:
        """Reset all state - clear all loaded games and reload examples."""
        store = get_game_store()
        count = len(store.list())
        store.clear()
        load_example_games()
        logger.info(
            "Reset state. Cleared %d games, restored %d examples.", count, len(store.list())
        )
        return {"status": "reset", "games_cleared": count}


@app.get("/api/plugins/status")
def get_plugin_status() -> list[dict]:
    """Return status of all managed plugins."""
    # Register any newly-ready plugins
    register_healthy_plugins()

    loading = plugin_manager.loading_status
    statuses = []

    for name, pp in plugin_manager.plugins.items():
        # Determine status string
        if pp.healthy:
            status_str = "ready"
        elif name in loading.get("plugins_loading", []):
            status_str = "loading"
        elif pp.info.get("error"):
            status_str = "degraded"
        else:
            status_str = "unavailable"

        status: dict = {
            "name": name,
            "status": status_str,
            "healthy": pp.healthy,
            "url": pp.url if pp.healthy else None,
            "analyses": [a.get("name") for a in pp.analyses] if pp.healthy else [],
        }
        # Include compile_targets if the plugin advertises them
        if pp.healthy and pp.info.get("compile_targets"):
            status["compile_targets"] = pp.info["compile_targets"]
        # Include error message for degraded plugins
        if pp.info.get("error"):
            status["error"] = pp.info["error"]
        statuses.append(status)
    return statuses


@app.get("/api/plugins/check-applicable/{game_id}")
def check_applicable(game_id: str) -> dict:
    """Check which analyses are applicable to a given game.

    For each analysis:
    1. Check if game can be converted to the required format (orchestrator's job)
    2. If convertible, ask plugin about game-specific constraints
    3. Plugin only checks constraints like "is zero-sum?", not format availability
    """
    store = get_game_store()
    game = store.get(game_id)
    if game is None:
        return {"error": f"Game not found: {game_id}"}

    conversion_registry = get_conversion_registry()
    results: dict[str, dict] = {}

    # Cache converted game dicts to avoid redundant serialization
    converted_games: dict[str, dict] = {}

    def get_game_in_format(target_format: str) -> tuple[dict | None, str | None]:
        """Get game data in target format, from store cache. Returns (game_data, error)."""
        if target_format in converted_games:
            return converted_games[target_format], None

        converted = store.get_converted(game_id, target_format)
        if converted:
            game_data = converted.model_dump()
            converted_games[target_format] = game_data
            return game_data, None

        # Check why conversion failed
        check = conversion_registry.check(game, target_format, quick=True)
        reason = ", ".join(check.blockers) if check.blockers else "no conversion path"
        return None, f"Cannot convert to {target_format}: {reason}"

    for _name, pp in plugin_manager.plugins.items():
        if not pp.healthy or not pp.url:
            continue

        for analysis in pp.analyses:
            analysis_name = analysis.get("name")
            if not analysis_name:
                continue

            applicable_to = analysis.get("applicable_to", [])
            if not applicable_to:
                # No format requirement - always applicable
                results[analysis_name] = {"applicable": True}
                continue

            # Find a format we can provide
            game_data = None
            format_error = None
            for target_format in applicable_to:
                game_data, format_error = get_game_in_format(target_format)
                if game_data is not None:
                    break

            if game_data is None:
                # Can't convert to any required format
                results[analysis_name] = {"applicable": False, "reason": format_error}
                continue

            # Format is available - ask plugin about game-specific constraints
            try:
                response = httpx.post(
                    f"{pp.url}/check-applicable",
                    json={"game": game_data},
                    timeout=2.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    plugin_result = data.get("analyses", {}).get(analysis_name)
                    if plugin_result:
                        results[analysis_name] = plugin_result
                    else:
                        results[analysis_name] = {"applicable": True}
                elif response.status_code == 404:
                    # Plugin doesn't support check-applicable - format is enough
                    results[analysis_name] = {"applicable": True}
                else:
                    results[analysis_name] = {"applicable": True}
            except httpx.RequestError:
                # Plugin unreachable - assume applicable if format works
                results[analysis_name] = {"applicable": True}

    return {"game_id": game_id, "analyses": results}


@app.post("/api/compile/{plugin_name}/{target}")
def compile_game(plugin_name: str, target: str, request: dict) -> dict:
    """Proxy compile request to a plugin.

    Request body should contain: { source_code: str, filename?: str }
    """
    pp = plugin_manager.get_plugin(plugin_name)
    if pp is None or not pp.healthy:
        raise HTTPException(
            status_code=404, detail=f"Plugin '{plugin_name}' not found or unhealthy"
        )

    # Forward request to plugin
    try:
        resp = httpx.post(
            f"{pp.url}/compile/{target}",
            json=request,
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        detail = e.response.json() if e.response.content else str(e)
        raise HTTPException(status_code=e.response.status_code, detail=detail) from e
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Plugin communication error: {e}") from e


mount_frontend(app)
