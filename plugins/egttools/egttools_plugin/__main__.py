"""EGTTools plugin service entrypoint.

Run with: python -m egttools_plugin --port=PORT
Implements the plugin HTTP contract (API v1).
"""

from __future__ import annotations

import argparse
import logging
import threading
import uuid
from concurrent.futures import ProcessPoolExecutor, Future
from enum import Enum
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from egttools_plugin.replicator import run_replicator_dynamics
from egttools_plugin.fixation import run_evolutionary_stability

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("egttools_plugin")

PLUGIN_VERSION = "0.1.0"
API_VERSION = 1

# ---------------------------------------------------------------------------
# Analysis registry
# ---------------------------------------------------------------------------

ANALYSES = {
    "Replicator Dynamics": {
        "name": "Replicator Dynamics",
        "description": "Simulate strategy evolution in infinite populations using the replicator equation.",
        "applicable_to": ["normal"],
        "continuous": False,
        "config_schema": {
            "time_steps": {
                "type": "integer",
                "default": 100,
                "description": "Number of simulation steps",
            },
            "initial_population": {
                "type": "array",
                "description": "Initial strategy frequencies (defaults to uniform)",
            },
            "dt": {
                "type": "number",
                "default": 0.01,
                "description": "Time step size",
            },
        },
        "run": run_replicator_dynamics,
    },
    "Evolutionary Stability": {
        "name": "Evolutionary Stability",
        "description": "Analyze evolutionary stability using finite population dynamics (Moran process).",
        "applicable_to": ["normal"],
        "continuous": False,
        "config_schema": {
            "population_size": {
                "type": "integer",
                "default": 100,
                "description": "Population size Z",
            },
            "mutation_rate": {
                "type": "number",
                "default": 0.001,
                "description": "Mutation rate mu",
            },
            "intensity_of_selection": {
                "type": "number",
                "default": 1.0,
                "description": "Selection strength beta",
            },
        },
        "run": run_evolutionary_stability,
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
    from egttools_plugin.replicator import run_replicator_dynamics
    from egttools_plugin.fixation import run_evolutionary_stability

    runners = {
        "Replicator Dynamics": run_replicator_dynamics,
        "Evolutionary Stability": run_evolutionary_stability,
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


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="EGTTools Plugin", version=PLUGIN_VERSION)


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
        "conversions": [],
    }


class CheckApplicableRequest(BaseModel):
    game: dict[str, Any]


@app.post("/check-applicable")
def check_applicable(req: CheckApplicableRequest) -> dict:
    """Check game-specific constraints for each analysis.

    The orchestrator already verified format compatibility and conversion.
    This endpoint only checks game-specific constraints.
    """
    results = {}

    for name, analysis in ANALYSES.items():
        # All EGTTools analyses require symmetric games (square payoff matrix)
        payoffs = req.game.get("payoffs", [])
        if payoffs:
            n_rows = len(payoffs)
            n_cols = len(payoffs[0]) if payoffs else 0
            if n_rows != n_cols:
                results[name] = {
                    "applicable": False,
                    "reason": f"Requires symmetric game (got {n_rows}x{n_cols})",
                }
                continue

        results[name] = {"applicable": True}

    return {"analyses": results}


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

    task_id = f"egt-{uuid.uuid4().hex[:8]}"
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
    parser = argparse.ArgumentParser(description="EGTTools plugin service")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    logger.info("Starting EGTTools plugin on %s:%d", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
