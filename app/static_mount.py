from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

def mount_frontend(app: FastAPI) -> None:
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    dist_dir = frontend_dir / "dist"
    static_dir = dist_dir if dist_dir.exists() else frontend_dir

    # Serve built assets
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    index = static_dir / "index.html"

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(index)
