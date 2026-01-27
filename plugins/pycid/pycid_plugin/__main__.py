"""PyCID plugin service entrypoint.

Run with: python -m pycid_plugin --port=PORT
Implements the plugin HTTP contract (API v1).
"""
from __future__ import annotations

import argparse
import logging
import threading
import uuid
from enum import Enum
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pycid_plugin.nash import run_maid_nash

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pycid_plugin")

PLUGIN_VERSION = "0.1.0"
API_VERSION = 1

# ---------------------------------------------------------------------------
# Analysis registry
# ---------------------------------------------------------------------------

ANALYSES = {
    "MAID Nash Equilibrium": {
        "name": "MAID Nash Equilibrium",
        "description": "Computes Nash equilibria for Multi-Agent Influence Diagrams using PyCID.",
        "applicable_to": ["maid"],
        "continuous": True,
        "config_schema": {
            "solver": {
                "type": "string",
                "enum": ["auto", "enummixed", "enumpure", "simpdiv", "lcp"],
            },
        },
        "run": run_maid_nash,
    },
}

# ---------------------------------------------------------------------------
# Task state
# ---------------------------------------------------------------------------


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskState:
    def __init__(self) -> None:
        self.status: TaskStatus = TaskStatus.QUEUED
        self.result: dict[str, Any] | None = None
        self.error: dict[str, Any] | None = None
        self.cancelled = threading.Event()

    def to_dict(self, task_id: str) -> dict[str, Any]:
        d: dict[str, Any] = {"task_id": task_id, "status": self.status.value}
        if self.result is not None:
            d["result"] = self.result
        if self.error is not None:
            d["error"] = self.error
        return d


_tasks: dict[str, TaskState] = {}
_tasks_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    analysis: str
    game: dict[str, Any]
    config: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="PyCID Plugin", version=PLUGIN_VERSION)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "plugin_version": PLUGIN_VERSION,
    }


@app.get("/info")
def info() -> dict:
    analyses_info = []
    for a in ANALYSES.values():
        analyses_info.append({
            "name": a["name"],
            "description": a["description"],
            "applicable_to": a["applicable_to"],
            "continuous": a["continuous"],
            "config_schema": a["config_schema"],
        })
    return {
        "api_version": API_VERSION,
        "plugin_version": PLUGIN_VERSION,
        "analyses": analyses_info,
    }


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    analysis_entry = ANALYSES.get(req.analysis)
    if analysis_entry is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "UNSUPPORTED_ANALYSIS",
                    "message": f"Unknown analysis: {req.analysis}. Available: {list(ANALYSES.keys())}",
                }
            },
        )

    game_format = req.game.get("format_name", "")
    if game_format not in analysis_entry["applicable_to"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_GAME",
                    "message": f"Game format '{game_format}' not supported by {req.analysis}",
                }
            },
        )

    task_id = f"p-{uuid.uuid4().hex[:8]}"
    task = TaskState()

    with _tasks_lock:
        _tasks[task_id] = task

    def _run() -> None:
        task.status = TaskStatus.RUNNING
        try:
            if task.cancelled.is_set():
                task.status = TaskStatus.CANCELLED
                return

            result = analysis_entry["run"](req.game, req.config)

            if task.cancelled.is_set():
                task.status = TaskStatus.CANCELLED
                return

            task.result = result
            task.status = TaskStatus.DONE
        except ValueError as e:
            task.error = {"code": "INVALID_CONFIG", "message": str(e), "details": {}}
            task.status = TaskStatus.FAILED
        except Exception as e:
            logger.exception("Analysis %s failed", req.analysis)
            task.error = {"code": "INTERNAL", "message": str(e), "details": {}}
            task.status = TaskStatus.FAILED

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {"task_id": task_id, "status": "queued"}


@app.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    with _tasks_lock:
        task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return task.to_dict(task_id)


@app.post("/cancel/{task_id}")
def cancel_task(task_id: str) -> dict:
    with _tasks_lock:
        task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    task.cancelled.set()
    return {"task_id": task_id, "cancelled": True}


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="PyCID plugin service")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    logger.info("Starting PyCID plugin on %s:%d", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
