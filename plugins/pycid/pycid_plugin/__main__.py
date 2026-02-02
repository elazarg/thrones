"""PyCID plugin service entrypoint.

Run with: python -m pycid_plugin --port=PORT
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

from pycid_plugin.cid_analysis import (
    run_decision_relevance,
    run_value_of_control,
    run_value_of_information,
)
from pycid_plugin.convert import convert_maid_to_efg
from pycid_plugin.nash import run_maid_nash
from pycid_plugin.spe import run_maid_spe
from pycid_plugin.verify_profile import run_verify_profile

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
        "description": "Computes pure-strategy Nash equilibria for Multi-Agent Influence Diagrams using PyCID.",
        "applicable_to": ["maid"],
        "continuous": True,
        "config_schema": {},  # PyCID only supports pure NE enumeration
        "run": run_maid_nash,
    },
    "MAID Subgame Perfect Equilibrium": {
        "name": "MAID Subgame Perfect Equilibrium",
        "description": "Computes pure-strategy subgame perfect equilibria (SPE) for MAIDs.",
        "applicable_to": ["maid"],
        "continuous": True,
        "config_schema": {},  # PyCID only supports pure SPE enumeration
        "run": run_maid_spe,
    },
    "MAID Verify Profile": {
        "name": "MAID Verify Profile",
        "description": "Check if a strategy profile is a Nash equilibrium for the MAID",
        "applicable_to": ["maid"],
        "continuous": False,
        "config_schema": {
            "profile": {
                "type": "object",
                "description": "Strategy profile: {agent: {decision: action}}",
            },
        },
        "run": run_verify_profile,
    },
    "Value of Information": {
        "name": "Value of Information",
        "description": "Compute how much observing a variable benefits a decision",
        "applicable_to": ["maid"],
        "continuous": False,
        "config_schema": {
            "decision": {
                "type": "string",
                "description": "The decision node ID",
            },
            "observation": {
                "type": "string",
                "description": "The observation node ID to evaluate",
            },
        },
        "run": run_value_of_information,
    },
    "Value of Control": {
        "name": "Value of Control",
        "description": "Compute how much controlling a variable benefits a decision",
        "applicable_to": ["maid"],
        "continuous": False,
        "config_schema": {
            "decision": {
                "type": "string",
                "description": "The decision node ID",
            },
            "variable": {
                "type": "string",
                "description": "The variable node ID to evaluate control over",
            },
        },
        "run": run_value_of_control,
    },
    "Decision Relevance": {
        "name": "Decision Relevance",
        "description": "Analyze strategic dependencies between decisions (r-reachability and s-reachability)",
        "applicable_to": ["maid"],
        "continuous": False,
        "config_schema": {},
        "run": run_decision_relevance,
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
    from pycid_plugin.cid_analysis import (
        run_decision_relevance,
        run_value_of_control,
        run_value_of_information,
    )
    from pycid_plugin.nash import run_maid_nash
    from pycid_plugin.spe import run_maid_spe
    from pycid_plugin.verify_profile import run_verify_profile

    runners = {
        "MAID Nash Equilibrium": run_maid_nash,
        "MAID Subgame Perfect Equilibrium": run_maid_spe,
        "MAID Verify Profile": run_verify_profile,
        "Value of Information": run_value_of_information,
        "Value of Control": run_value_of_control,
        "Decision Relevance": run_decision_relevance,
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


class ConvertRequest(BaseModel):
    game: dict[str, Any]


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
        "conversions": [
            {"source": "maid", "target": "extensive"},
        ],
    }


@app.post("/convert/{source}-to-{target}")
def convert_endpoint(source: str, target: str, req: ConvertRequest) -> dict:
    """Convert a game from one format to another."""
    if source == "maid" and target == "extensive":
        try:
            result = convert_maid_to_efg(req.game)
            return {"game": result}
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "CONVERSION_ERROR",
                        "message": str(e),
                    }
                },
            )
        except Exception as e:
            logger.exception("Conversion %s-to-%s failed", source, target)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "code": "INTERNAL",
                        "message": f"Conversion failed: {e}",
                    }
                },
            )

    raise HTTPException(
        status_code=400,
        detail={
            "error": {
                "code": "UNSUPPORTED_CONVERSION",
                "message": f"Unsupported conversion: {source} to {target}",
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
    parser = argparse.ArgumentParser(description="PyCID plugin service")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    logger.info("Starting PyCID plugin on %s:%d", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
