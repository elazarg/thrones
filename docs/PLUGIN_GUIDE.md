# Plugin Development Guide

This guide explains how to create analysis plugins for the Game Theory Workbench.

## Overview

Plugins extend the workbench with new analysis algorithms, format support, and game conversions. There are two types:

| Type | Location | Use When |
|------|----------|----------|
| **Local** | `app/plugins/` | No external dependencies beyond the main app |
| **Remote** | `plugins/*/` | Needs isolated dependencies (e.g., specific library versions) |

## Plugin Capabilities

Plugins can provide:
- **Analyses**: Nash equilibrium, IESDS, dominance detection, etc.
- **Format Parsers**: EFG, NFG, custom formats
- **Conversions**: Transform between game representations

---

## Creating a Local Plugin

Local plugins are Python modules that run in-process with the main application.

### Step 1: Create the Plugin File

Create `app/plugins/my_analysis.py`:

```python
"""My custom analysis plugin."""
from __future__ import annotations

from app.core.registry import AnalysisResult
from app.dependencies import get_registry
from app.models import AnyGame, ExtensiveFormGame


class MyAnalysisPlugin:
    """Describe what your analysis does."""

    name = "My Analysis"
    description = "Computes something interesting about the game"
    applicable_to: tuple[str, ...] = ("extensive", "normal")  # Game formats
    continuous = True  # Run automatically when game changes?

    def can_run(self, game: AnyGame) -> bool:
        """Return True if this analysis can run on the given game."""
        # Example: only run on 2-player games
        return len(game.players) == 2

    def run(self, game: AnyGame, config: dict | None = None) -> AnalysisResult:
        """Execute the analysis and return results."""
        # Your analysis logic here
        result_data = {"finding": "something interesting"}

        return AnalysisResult(
            summary=self.summarize_result(result_data),
            details=result_data,
        )

    def summarize_result(self, result: dict) -> str:
        """Generate a one-line summary for the status bar."""
        return f"Found: {result['finding']}"

    def summarize(self, result: AnalysisResult) -> str:
        """Generate summary from AnalysisResult."""
        return result.summary


# Register the plugin at import time
get_registry().register_analysis(MyAnalysisPlugin())
```

### Step 2: Import for Registration

Add the import to `app/plugins/__init__.py`:

```python
from app.plugins import my_analysis  # Triggers registration
```

### Step 3: Test Your Plugin

```python
# tests/test_plugins/test_my_analysis.py
import pytest
from app.plugins.my_analysis import MyAnalysisPlugin
from app.models import ExtensiveFormGame

def test_my_analysis_runs():
    plugin = MyAnalysisPlugin()
    game = ...  # Create or load a test game

    result = plugin.run(game)

    assert result.summary
    assert "finding" in result.details
```

### Local Plugin Protocol

Your plugin class must implement the `AnalysisPlugin` protocol:

```python
class AnalysisPlugin(Protocol):
    name: str
    description: str
    applicable_to: tuple[str, ...]  # "extensive", "normal", "maid"
    continuous: bool

    def can_run(self, game: AnyGame) -> bool: ...
    def run(self, game: AnyGame, config: dict | None = None) -> AnalysisResult: ...
    def summarize(self, result: AnalysisResult) -> str: ...
```

---

## Creating a Remote Plugin

Remote plugins run as isolated FastAPI services in their own Python virtual environments.

### Step 1: Create Directory Structure

```
plugins/
└── myplugin/
    ├── myplugin_plugin/
    │   ├── __init__.py
    │   └── __main__.py      # Service entrypoint
    ├── pyproject.toml        # Dependencies
    └── tests/
        └── test_analysis.py
```

### Step 2: Define Dependencies

`plugins/myplugin/pyproject.toml`:

```toml
[project]
name = "myplugin-plugin"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn>=0.27.0",
    "pydantic>=2.6.0",
    # Add your specific dependencies here
    "some-library==1.2.3",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
]
```

### Step 3: Implement the HTTP Service

`plugins/myplugin/myplugin_plugin/__main__.py`:

```python
"""My plugin service entrypoint."""
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("myplugin")

PLUGIN_VERSION = "0.1.0"
API_VERSION = 1


# Task state management
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


# Request models
class AnalyzeRequest(BaseModel):
    analysis: str
    game: dict[str, Any]
    config: dict[str, Any] = {}


# Analysis implementation
def run_my_analysis(game: dict, config: dict) -> dict:
    """Your analysis logic here."""
    # Process the game dict and return results
    return {
        "summary": "Analysis complete",
        "details": {"finding": "something"}
    }


# Analysis registry
ANALYSES = {
    "My Analysis": {
        "name": "My Analysis",
        "description": "Computes something interesting",
        "applicable_to": ["extensive", "normal"],
        "continuous": True,
        "config_schema": {},
        "run": run_my_analysis,
    },
}


# FastAPI app
app = FastAPI(title="My Plugin", version=PLUGIN_VERSION)


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "plugin_version": PLUGIN_VERSION,
    }


@app.get("/info")
def info() -> dict:
    """Plugin information and capabilities."""
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
        "formats": [],  # Add [".xyz"] if you support format parsing
    }


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    """Submit an analysis task."""
    analysis_entry = ANALYSES.get(req.analysis)
    if analysis_entry is None:
        raise HTTPException(status_code=400, detail={
            "error": {"code": "UNSUPPORTED_ANALYSIS", "message": f"Unknown: {req.analysis}"}
        })

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
            task.result = analysis_entry["run"](req.game, req.config)
            task.status = TaskStatus.DONE
        except Exception as e:
            logger.exception("Analysis failed")
            task.error = {"code": "INTERNAL", "message": str(e)}
            task.status = TaskStatus.FAILED

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {"task_id": task_id, "status": "queued"}


@app.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    """Get task status and result."""
    with _tasks_lock:
        task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return task.to_dict(task_id)


@app.post("/cancel/{task_id}")
def cancel_task(task_id: str) -> dict:
    """Request task cancellation."""
    with _tasks_lock:
        task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    task.cancelled.set()
    return {"task_id": task_id, "cancelled": True}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    logger.info("Starting plugin on %s:%d", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
```

### Step 4: Configure the Plugin

Add to `plugins.toml` in the project root:

```toml
[[plugins]]
name = "myplugin"
command = ["plugins/myplugin/.venv/Scripts/python", "-m", "myplugin_plugin"]
cwd = "plugins/myplugin"
auto_start = true
restart = "on-failure"
```

### Step 5: Set Up the Plugin Venv

```powershell
# Windows
cd plugins/myplugin
py -3.12 -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
```

```bash
# Unix
cd plugins/myplugin
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

---

## HTTP Contract (API v1)

All remote plugins must implement these endpoints:

### `GET /health`

Health check for plugin readiness.

**Response:**
```json
{
  "status": "ok",
  "api_version": 1,
  "plugin_version": "0.1.0"
}
```

### `GET /info`

Plugin capabilities and metadata.

**Response:**
```json
{
  "api_version": 1,
  "plugin_version": "0.1.0",
  "analyses": [
    {
      "name": "My Analysis",
      "description": "What it does",
      "applicable_to": ["extensive", "normal"],
      "continuous": true,
      "config_schema": {}
    }
  ],
  "formats": [".xyz"],
  "conversions": []
}
```

### `POST /analyze`

Submit an analysis task.

**Request:**
```json
{
  "analysis": "My Analysis",
  "game": { /* game dict */ },
  "config": {}
}
```

**Response:**
```json
{
  "task_id": "p-abc12345",
  "status": "queued"
}
```

### `GET /tasks/{task_id}`

Poll for task completion.

**Response (in progress):**
```json
{
  "task_id": "p-abc12345",
  "status": "running"
}
```

**Response (complete):**
```json
{
  "task_id": "p-abc12345",
  "status": "done",
  "result": {
    "summary": "Found 2 equilibria",
    "details": { /* analysis-specific */ }
  }
}
```

**Response (failed):**
```json
{
  "task_id": "p-abc12345",
  "status": "failed",
  "error": {
    "code": "INTERNAL",
    "message": "Description of what went wrong"
  }
}
```

### `POST /cancel/{task_id}`

Request task cancellation.

**Response:**
```json
{
  "task_id": "p-abc12345",
  "cancelled": true
}
```

### `POST /parse/{format}` (Optional)

Parse a game file format.

**Request:**
```json
{
  "content": "... file content ...",
  "filename": "game.xyz"
}
```

**Response:**
```json
{
  "game": { /* parsed game dict */ }
}
```

---

## Task Status Values

### Plugin-Side Status

| Status | Meaning |
|--------|---------|
| `queued` | Task received, waiting to start |
| `running` | Analysis in progress |
| `done` | Completed successfully, result available |
| `failed` | Error occurred, error details available |
| `cancelled` | Cancellation request honored |

### Backend-Side Status

The main app maps plugin status to its own values:

| Backend | Plugin |
|---------|--------|
| `pending` | `queued` |
| `running` | `running` |
| `completed` | `done` |
| `failed` | `failed` |
| `cancelled` | `cancelled` |

---

## Testing

### Unit Tests

Test your analysis logic independently:

```python
# plugins/myplugin/tests/test_analysis.py
from myplugin_plugin import run_my_analysis

def test_basic_analysis():
    game = {
        "id": "test",
        "format_name": "extensive",
        "players": ["A", "B"],
        # ... rest of game structure
    }

    result = run_my_analysis(game, {})

    assert "summary" in result
    assert "details" in result
```

### Integration Tests

Test the full HTTP flow:

```python
# plugins/myplugin/tests/test_integration.py
from fastapi.testclient import TestClient
from myplugin_plugin.__main__ import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_analyze_workflow():
    # Submit task
    response = client.post("/analyze", json={
        "analysis": "My Analysis",
        "game": {"id": "test", "format_name": "extensive", ...},
        "config": {}
    })
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    # Poll until complete
    import time
    for _ in range(10):
        response = client.get(f"/tasks/{task_id}")
        if response.json()["status"] == "done":
            break
        time.sleep(0.1)

    assert response.json()["status"] == "done"
    assert "result" in response.json()
```

---

## Future Plugin Ideas

See [potential-plugins.md](potential-plugins.md) for a curated list of libraries that could be wrapped as plugins:

| Library | Purpose |
|---------|---------|
| **OpenSpiel** | CFR, imperfect-information algorithms |
| **Nashpy** | 2-player matrix game solvers |
| **pyAgrum** | Influence diagrams, LIMID solving |
| **lrslib** | Vertex enumeration for equilibria |
| **EGTTools** | Evolutionary game dynamics |

---

## Best Practices

1. **Keep plugins focused**: One plugin = one library or family of algorithms
2. **Handle errors gracefully**: Return proper error codes, don't crash
3. **Support cancellation**: Check `cancelled.is_set()` in long computations
4. **Document config options**: Use `config_schema` in `/info` response
5. **Test independently**: Each plugin should have its own test suite
6. **Pin dependencies**: Avoid version conflicts with explicit version specs
