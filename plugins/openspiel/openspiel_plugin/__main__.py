"""OpenSpiel plugin service entrypoint.

Run with: python -m openspiel_plugin --port=PORT
Implements the plugin HTTP contract (API v1).

NOTE: OpenSpiel only works on Linux/macOS. On Windows, this plugin
will start but return an error status explaining that WSL is required.
"""
from __future__ import annotations

import argparse
import logging
import sys
import threading
import uuid
from enum import Enum
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("openspiel_plugin")

PLUGIN_VERSION = "0.1.0"
API_VERSION = 1

# Check platform compatibility
IS_WINDOWS = sys.platform == "win32"
PLATFORM_ERROR = (
    "OpenSpiel is not available on Windows. "
    "Please use WSL (Windows Subsystem for Linux) to run this plugin. "
    "See plugins/openspiel/README.md for setup instructions."
)

# ---------------------------------------------------------------------------
# Analysis registry (only load if not Windows)
# ---------------------------------------------------------------------------

if not IS_WINDOWS:
    from openspiel_plugin.cfr import run_cfr_equilibrium, run_best_response
    from openspiel_plugin.exploitability import (
        run_exploitability,
        run_policy_exploitability,
    )

    ANALYSES = {
        "CFR Equilibrium": {
            "name": "CFR Equilibrium",
            "description": "Compute approximate Nash equilibrium using Counterfactual Regret Minimization.",
            "applicable_to": ["extensive"],
            "continuous": False,
            "config_schema": {
                "iterations": {
                    "type": "integer",
                    "default": 1000,
                    "description": "Number of CFR iterations",
                },
                "algorithm": {
                    "type": "string",
                    "enum": ["cfr", "cfr+", "mccfr"],
                    "default": "cfr+",
                    "description": "CFR algorithm variant",
                },
            },
            "run": run_cfr_equilibrium,
        },
        "Exploitability": {
            "name": "Exploitability",
            "description": "Measure distance from Nash equilibrium (nash_conv).",
            "applicable_to": ["extensive"],
            "continuous": False,
            "config_schema": {},
            "run": run_exploitability,
        },
        "CFR Convergence": {
            "name": "CFR Convergence",
            "description": "Run CFR and track exploitability over iterations.",
            "applicable_to": ["extensive"],
            "continuous": False,
            "config_schema": {
                "iterations": {
                    "type": "integer",
                    "default": 1000,
                    "description": "Number of CFR iterations",
                },
                "algorithm": {
                    "type": "string",
                    "enum": ["cfr", "cfr+"],
                    "default": "cfr+",
                    "description": "CFR algorithm variant",
                },
            },
            "run": run_policy_exploitability,
        },
        "Best Response": {
            "name": "Best Response",
            "description": "Compute optimal counter-strategy to a policy.",
            "applicable_to": ["extensive"],
            "continuous": False,
            "config_schema": {
                "player": {
                    "type": "integer",
                    "default": 0,
                    "description": "Player index to compute best response for",
                },
            },
            "run": run_best_response,
        },
    }
else:
    ANALYSES = {}

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

app = FastAPI(title="OpenSpiel Plugin", version=PLUGIN_VERSION)


@app.get("/health")
def health() -> dict:
    if IS_WINDOWS:
        return {
            "status": "error",
            "api_version": API_VERSION,
            "plugin_version": PLUGIN_VERSION,
            "error": PLATFORM_ERROR,
        }
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "plugin_version": PLUGIN_VERSION,
    }


@app.get("/info")
def info() -> dict:
    if IS_WINDOWS:
        return {
            "api_version": API_VERSION,
            "plugin_version": PLUGIN_VERSION,
            "analyses": [],
            "conversions": [],
            "error": PLATFORM_ERROR,
        }

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
        "conversions": [],
    }


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    if IS_WINDOWS:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "PLATFORM_NOT_SUPPORTED",
                    "message": PLATFORM_ERROR,
                }
            },
        )

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

    task_id = f"os-{uuid.uuid4().hex[:8]}"
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
    parser = argparse.ArgumentParser(description="OpenSpiel plugin service")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    if IS_WINDOWS:
        logger.warning("OpenSpiel plugin running on Windows - functionality limited")
        logger.warning(PLATFORM_ERROR)

    logger.info("Starting OpenSpiel plugin on %s:%d", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
