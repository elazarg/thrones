"""OpenSpiel plugin service entrypoint.

Run with: python -m openspiel_plugin --port=PORT
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("openspiel_plugin")

PLUGIN_VERSION = "0.1.0"
API_VERSION = 1

# ---------------------------------------------------------------------------
# Analysis registry
# ---------------------------------------------------------------------------

from openspiel_plugin.cfr import run_best_response, run_cfr_equilibrium, run_fictitious_play
from openspiel_plugin.exploitability import (
    check_zero_sum,
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
        "description": "Measure distance from Nash equilibrium (nash_conv). Requires zero-sum games.",
        "applicable_to": ["extensive"],
        "continuous": False,
        "config_schema": {},
        "run": run_exploitability,
        "check_applicable": check_zero_sum,
    },
    "CFR Convergence": {
        "name": "CFR Convergence",
        "description": "Run CFR and track exploitability over iterations. Requires zero-sum games.",
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
        "check_applicable": check_zero_sum,
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
    "Fictitious Play": {
        "name": "Fictitious Play",
        "description": "Compute Nash equilibrium using Fictitious Play (iterative best-response to empirical distribution)",
        "applicable_to": ["extensive"],
        "continuous": False,
        "config_schema": {
            "iterations": {
                "type": "integer",
                "default": 1000,
                "description": "Number of Fictitious Play iterations",
            },
        },
        "run": run_fictitious_play,
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
    from openspiel_plugin.cfr import run_best_response, run_cfr_equilibrium, run_fictitious_play
    from openspiel_plugin.exploitability import run_exploitability, run_policy_exploitability

    runners = {
        "CFR Equilibrium": run_cfr_equilibrium,
        "Exploitability": run_exploitability,
        "CFR Convergence": run_policy_exploitability,
        "Best Response": run_best_response,
        "Fictitious Play": run_fictitious_play,
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


class CheckApplicableRequest(BaseModel):
    game: dict[str, Any]


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="OpenSpiel Plugin", version=PLUGIN_VERSION)


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


@app.post("/check-applicable")
def check_applicable(req: CheckApplicableRequest) -> dict:
    """Check game-specific constraints for each analysis.

    The orchestrator already verified format compatibility and conversion.
    This endpoint only checks game-specific constraints (e.g., zero-sum requirement).
    """
    results = {}

    for name, analysis in ANALYSES.items():
        # Check analysis-specific constraints (e.g., zero-sum for Exploitability)
        check_fn = analysis.get("check_applicable")
        if check_fn:
            check_result = check_fn(req.game)
            if not check_result.get("applicable", True):
                results[name] = {
                    "applicable": False,
                    "reason": check_result.get("reason", "Not applicable"),
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

    # Check analysis-specific constraints (orchestrator handles format conversion)
    check_fn = analysis_entry.get("check_applicable")
    if check_fn:
        check_result = check_fn(req.game)
        if not check_result.get("applicable", True):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_GAME",
                        "message": check_result.get("reason", "Game not compatible"),
                    }
                },
            )

    task_id = f"os-{uuid.uuid4().hex[:8]}"
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
    parser = argparse.ArgumentParser(description="OpenSpiel plugin service")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    logger.info("Starting OpenSpiel plugin on %s:%d", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
