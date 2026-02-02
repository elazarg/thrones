from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import IS_PRODUCTION

logger = logging.getLogger(__name__)


def mount_frontend(app: FastAPI) -> None:
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    dist_dir = frontend_dir / "dist"

    # In production, require built frontend; in development, allow fallback
    if IS_PRODUCTION:
        if not dist_dir.exists():
            logger.warning(
                "Production mode: frontend/dist not found. "
                "Static files will not be served. "
                "Build frontend with 'npm run build' or set ENVIRONMENT=development."
            )
            return
        static_dir = dist_dir
    else:
        static_dir = dist_dir if dist_dir.exists() else frontend_dir

    # Only mount static files if directory exists (not in Docker API-only mode)
    if not static_dir.exists():
        return

    # Serve built assets
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    index = static_dir / "index.html"

    # In production, verify index.html exists before mounting SPA fallback
    if IS_PRODUCTION and not index.exists():
        logger.warning(
            "Production mode: index.html not found in dist/. SPA fallback will not be mounted."
        )
        return

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(index)
