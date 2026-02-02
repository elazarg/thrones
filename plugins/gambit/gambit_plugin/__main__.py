"""Gambit plugin service entrypoint.

Run with: python -m gambit_plugin --port=PORT
Implements the plugin HTTP contract (API v1).
"""

from __future__ import annotations

import argparse
import logging
import threading
import uuid
from concurrent.futures import Future, ProcessPoolExecutor
from enum import Enum
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from gambit_plugin.backward_induction import run_backward_induction
from gambit_plugin.iesds import run_iesds, run_weak_iesds
from gambit_plugin.levelk import run_levelk
from gambit_plugin.nash import run_nash
from gambit_plugin.parsers import parse_efg, parse_nfg
from gambit_plugin.qre import run_qre
from gambit_plugin.supports import run_support_enum
from gambit_plugin.verify_profile import run_verify_profile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("gambit_plugin")

PLUGIN_VERSION = "0.1.0"
API_VERSION = 1

# ---------------------------------------------------------------------------
# Analysis registry
# ---------------------------------------------------------------------------

ANALYSES = {
    "Nash Equilibrium": {
        "name": "Nash Equilibrium",
        "description": "Computes Nash equilibria using Gambit solvers.",
        "applicable_to": ["extensive", "normal"],
        "continuous": True,
        "config_schema": {
            "solver": {
                "type": "string",
                "enum": [
                    "exhaustive",
                    "quick",
                    "pure",
                    "logit",
                    "approximate",
                    "lp",
                    "liap",
                ],
            },
            "max_equilibria": {"type": "integer"},
            "maxregret": {
                "type": "number",
                "description": "Max regret for liap solver (default 1e-6)",
            },
        },
        "run": run_nash,
    },
    "IESDS": {
        "name": "IESDS",
        "description": "Iterated Elimination of Strictly Dominated Strategies",
        "applicable_to": ["extensive", "normal"],
        "continuous": True,
        "config_schema": {},
        "run": run_iesds,
    },
    "Verify Profile": {
        "name": "Verify Profile",
        "description": "Check if a candidate profile is a Nash equilibrium",
        "applicable_to": ["extensive", "normal"],
        "continuous": False,
        "config_schema": {
            "profile": {"type": "object"},
        },
        "run": run_verify_profile,
    },
    "Quantal Response Equilibrium": {
        "name": "Quantal Response Equilibrium",
        "description": "Computes QRE, modeling bounded rationality where agents make errors proportional to cost",
        "applicable_to": ["extensive", "normal"],
        "continuous": True,
        "config_schema": {},
        "run": run_qre,
    },
    "Cognitive Hierarchy": {
        "name": "Cognitive Hierarchy",
        "description": "Level-K analysis: models strategic thinking at different levels of sophistication",
        "applicable_to": ["extensive", "normal"],
        "continuous": True,
        "config_schema": {
            "tau": {
                "type": "number",
                "description": "Poisson parameter for level distribution (default 1.5)",
            },
        },
        "run": run_levelk,
    },
    "Support Enumeration": {
        "name": "Support Enumeration",
        "description": "Enumerate all possible strategy support profiles that could be part of an equilibrium",
        "applicable_to": ["extensive", "normal"],
        "continuous": True,
        "config_schema": {},
        "run": run_support_enum,
    },
    "Backward Induction": {
        "name": "Backward Induction",
        "description": "Compute Subgame Perfect Equilibrium for perfect-information extensive-form games",
        "applicable_to": ["extensive"],
        "continuous": False,
        "config_schema": {},
        "run": run_backward_induction,
    },
    "Weak IESDS": {
        "name": "Weak IESDS",
        "description": "Iterated Elimination of Weakly Dominated Strategies (includes ties)",
        "applicable_to": ["extensive", "normal"],
        "continuous": True,
        "config_schema": {},
        "run": run_weak_iesds,
    },
}

# ---------------------------------------------------------------------------
# Process pool for CPU-bound analysis work
# ---------------------------------------------------------------------------

_executor: ProcessPoolExecutor | None = None


def _get_executor() -> ProcessPoolExecutor:
    """Get or create the process pool executor."""
    global _executor
    if _executor is None:
        _executor = ProcessPoolExecutor(max_workers=2)
    return _executor


def _run_analysis_in_process(analysis_name: str, game: dict, config: dict) -> dict:
    """Worker function that runs in a separate process.

    This function is called by ProcessPoolExecutor and must be picklable.
    It imports the analysis function fresh in the subprocess.
    """
    # Import inside the function to ensure it works in subprocess
    from gambit_plugin.backward_induction import run_backward_induction
    from gambit_plugin.iesds import run_iesds, run_weak_iesds
    from gambit_plugin.levelk import run_levelk
    from gambit_plugin.nash import run_nash
    from gambit_plugin.qre import run_qre
    from gambit_plugin.supports import run_support_enum
    from gambit_plugin.verify_profile import run_verify_profile

    runners = {
        "Nash Equilibrium": run_nash,
        "IESDS": run_iesds,
        "Verify Profile": run_verify_profile,
        "Quantal Response Equilibrium": run_qre,
        "Cognitive Hierarchy": run_levelk,
        "Support Enumeration": run_support_enum,
        "Backward Induction": run_backward_induction,
        "Weak IESDS": run_weak_iesds,
    }

    run_fn = runners.get(analysis_name)
    if run_fn is None:
        raise ValueError(f"Unknown analysis: {analysis_name}")

    return run_fn(game, config)


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
        self.future: Future | None = None

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


class ParseRequest(BaseModel):
    content: str
    filename: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Gambit Plugin", version=PLUGIN_VERSION)


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
        analyses_info.append(
            {
                "name": a["name"],
                "description": a["description"],
                "applicable_to": a["applicable_to"],
                "continuous": a["continuous"],
                "config_schema": a["config_schema"],
            }
        )
    return {
        "api_version": API_VERSION,
        "plugin_version": PLUGIN_VERSION,
        "analyses": analyses_info,
        "formats": [".efg", ".nfg"],
    }


@app.post("/parse/efg")
def parse_efg_endpoint(req: ParseRequest) -> dict:
    """Parse an EFG file and return game dict."""
    try:
        game = parse_efg(req.content, req.filename)
        return {"game": game}
    except Exception as e:
        logger.exception("EFG parsing failed for %s", req.filename)
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "PARSE_ERROR",
                    "message": f"Failed to parse EFG: {e}",
                }
            },
        )


@app.post("/parse/nfg")
def parse_nfg_endpoint(req: ParseRequest) -> dict:
    """Parse an NFG file and return game dict."""
    try:
        game = parse_nfg(req.content, req.filename)
        return {"game": game}
    except Exception as e:
        logger.exception("NFG parsing failed for %s", req.filename)
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "PARSE_ERROR",
                    "message": f"Failed to parse NFG: {e}",
                }
            },
        )


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

    # Submit to process pool for CPU-bound work
    executor = _get_executor()
    future = executor.submit(_run_analysis_in_process, req.analysis, req.game, req.config)
    task.future = future
    task.status = TaskStatus.RUNNING

    def _monitor_future() -> None:
        """Monitor the future and update task state when done."""
        try:
            if task.cancelled.is_set():
                future.cancel()
                task.status = TaskStatus.CANCELLED
                return

            # Wait for result (this blocks the monitor thread, not the main thread)
            result = future.result()

            if task.cancelled.is_set():
                task.status = TaskStatus.CANCELLED
                return

            task.result = result
            task.status = TaskStatus.DONE
        except Exception as e:
            logger.exception("Analysis %s failed", req.analysis)
            task.error = {"code": "INTERNAL", "message": str(e), "details": {}}
            task.status = TaskStatus.FAILED

    # Use a lightweight thread just to monitor the future
    monitor = threading.Thread(target=_monitor_future, daemon=True)
    monitor.start()

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
    if task.future:
        task.future.cancel()
    return {"task_id": task_id, "cancelled": True}


@app.on_event("shutdown")
def shutdown_executor() -> None:
    """Clean up the process pool on shutdown."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False)
        _executor = None


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Gambit plugin service")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    logger.info("Starting gambit plugin on %s:%d", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
