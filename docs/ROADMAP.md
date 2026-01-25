# Game Theory Workbench - Development Roadmap

## Overview

This document outlines the development roadmap for the Game Theory Workbench, covering architectural improvements, outstanding issues, and planned features.

**Current Version**: 0.3.0
**Last Updated**: January 2025

---

## 1. Current State Summary

### What Works Well

- **Plugin architecture** for extensible analysis algorithms
- **Format support** for EFG, NFG, and JSON with pygambit integration
- **Bidirectional conversion** between extensive and normal forms
- **Interactive visualization** with Pixi.js (pan/zoom/overlays)
- **Dual view modes** (game tree and payoff matrix)
- **Analysis overlays** (equilibrium highlighting, IESDS visualization)
- **69 backend tests** covering core functionality

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                             │
│  React 19 + Pixi.js 8 + Zustand 5 + TypeScript 5           │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐          │
│  │  Stores  │  │  Canvas  │  │    Components    │          │
│  │ (Zustand)│  │ (Pixi.js)│  │     (React)      │          │
│  └──────────┘  └──────────┘  └──────────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │ HTTP
┌─────────────────────────────────────────────────────────────┐
│                        Backend                              │
│  FastAPI + Pydantic + pygambit                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐          │
│  │  Models  │  │  Plugins │  │    Conversions   │          │
│  │          │  │ (Nash,   │  │   (EFG ↔ NFG)    │          │
│  │          │  │  IESDS)  │  │                  │          │
│  └──────────┘  └──────────┘  └──────────────────┘          │
│  ┌──────────────────────────────────────────────┐          │
│  │              GameStore (in-memory)           │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Outstanding Issues

Issues identified in code review that remain unaddressed.

### 2.1 Long-Running Computation Management

**Problem**: Nash equilibrium solvers (especially `enummixed_solve`) can run for extended periods on complex games. Currently:
- Computation blocks the request thread
- No way to cancel a running analysis
- No progress indication
- Server appears frozen to users

**Requirements**:
- Computations should not freeze the server
- Each computation should be "owned" (associated with a session/request)
- Users should be able to stop or pause long-running analyses
- Multiple users should be able to run analyses concurrently

**Proposed Solution**: See [Section 3.1 - Async Task System](#31-async-task-system)

### 2.2 Error Information Leakage

**Problem**: Exception messages passed directly to HTTP responses may leak internal paths or state.

**Locations**:
- `app/main.py:149` - `detail=str(e)` for ValueError
- `app/main.py:152` - `detail=f"Failed to parse game: {e}"`
- `app/main.py:204` - `details={"error": str(e)}`

**Fix**: Create sanitized error messages that don't expose internal details:

```python
# Before
raise HTTPException(status_code=400, detail=str(e))

# After
raise HTTPException(status_code=400, detail=sanitize_error(e, context="parsing"))
```

**Priority**: Medium
**Effort**: Small

### 2.3 Frontend Test Coverage

**Problem**: No tests for frontend logic, particularly the layout algorithms which are complex and critical.

**High-value test targets**:
- `frontend/src/canvas/layout/treeLayout.ts` - Pure function, easy to test
- `frontend/src/canvas/layout/matrixLayout.ts` - Pure function, easy to test
- `frontend/src/stores/*.ts` - State management logic

**Fix**: Add Vitest with tests for layout functions.

**Priority**: Medium
**Effort**: Medium

### 2.4 API Case Convention

**Problem**: Backend uses `snake_case` (Python convention), frontend receives as-is. JavaScript convention is `camelCase`.

**Examples**:
- `information_set` should be `informationSet` in frontend
- `normal_form` should be `normalForm`

**Options**:
1. **Pydantic alias_generator** - Transform on serialization
2. **Frontend transformation** - Transform on receipt
3. **Accept as-is** - Current approach, works but unconventional

**Priority**: Low
**Effort**: Medium (touches many files)

---

## 3. Architecture Improvements

### 3.1 Async Task System

A task management system for long-running computations.

#### Design Goals

1. **Non-blocking**: Analyses run without freezing HTTP request threads
2. **Owned**: Each task associated with a session/client
3. **Controllable**: Tasks can be cancelled, and potentially paused/resumed
4. **Observable**: Clients can poll for status and progress

#### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Task Manager                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    TaskRegistry                      │   │
│  │  task_id → { status, owner, result, cancel_event }  │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   ThreadPoolExecutor                 │   │
│  │            (bounded worker threads)                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

#### New Types

```python
# app/core/tasks.py

from enum import Enum
from dataclasses import dataclass
from threading import Event
from typing import Any
import uuid

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

@dataclass
class Task:
    id: str
    owner: str              # Session/client identifier
    status: TaskStatus
    plugin_name: str
    game_id: str
    config: dict
    result: Any | None
    error: str | None
    cancel_event: Event     # Set to request cancellation
    created_at: float
    started_at: float | None
    completed_at: float | None

class TaskManager:
    def submit(self, owner: str, game_id: str, plugin: str, config: dict) -> str:
        """Submit task, return task_id"""

    def get_status(self, task_id: str) -> Task | None:
        """Get task status and result if complete"""

    def cancel(self, task_id: str) -> bool:
        """Request task cancellation"""

    def list_tasks(self, owner: str) -> list[Task]:
        """List tasks for an owner"""

    def cleanup_old_tasks(self, max_age_seconds: int = 3600):
        """Remove completed tasks older than threshold"""
```

#### API Endpoints

```
POST   /api/tasks                    - Submit new analysis task
GET    /api/tasks/{task_id}          - Get task status/result
DELETE /api/tasks/{task_id}          - Cancel task
GET    /api/tasks?owner={owner}      - List tasks for owner
```

#### Plugin Cancellation Support

Plugins need to check for cancellation periodically:

```python
class NashPlugin:
    def run(self, game: AnyGame, config: dict | None = None) -> AnalysisResult:
        cancel_event = config.get("_cancel_event") if config else None

        for i, equilibrium in enumerate(solver.solve()):
            if cancel_event and cancel_event.is_set():
                return AnalysisResult(
                    summary="Cancelled",
                    details={"partial_results": results_so_far}
                )
            # ... process equilibrium
```

#### Frontend Integration

```typescript
// frontend/src/stores/analysisStore.ts

interface TaskState {
  taskId: string;
  status: 'pending' | 'running' | 'completed' | 'cancelled' | 'failed';
  result?: AnalysisResult;
}

// Poll for status until complete
async function pollTask(taskId: string): Promise<AnalysisResult> {
  while (true) {
    const task = await fetch(`/api/tasks/${taskId}`).then(r => r.json());
    if (task.status === 'completed') return task.result;
    if (task.status === 'failed') throw new Error(task.error);
    if (task.status === 'cancelled') throw new Error('Cancelled');
    await sleep(500); // Poll interval
  }
}
```

#### Implementation Phases

**Phase 1: Core Infrastructure**
1. Create `app/core/tasks.py` with TaskManager
2. Add task API endpoints
3. Update Nash plugin to check cancel_event
4. Add basic frontend polling

**Phase 2: Enhanced Control**
1. Add progress reporting to plugins
2. Add WebSocket support for real-time updates (optional)
3. Add task queue limits per owner
4. Add automatic cleanup of old tasks

**Phase 3: Advanced Features**
1. Pause/resume support (where solver permits)
2. Priority queuing
3. Persistent task history (SQLite)

---

### 3.2 Persistence Layer (Future)

Current state uses in-memory `GameStore`. For production:

**Options**:
1. **SQLite** - Simple, file-based, good for single-server
2. **Redis** - Fast, good for multi-worker deployment
3. **PostgreSQL** - Full-featured, good for complex queries

**Recommended approach**: Abstract `GameStore` behind interface, implement `SQLiteGameStore` for persistence.

```python
# app/core/store.py

from abc import ABC, abstractmethod

class GameStoreBase(ABC):
    @abstractmethod
    def add(self, game: AnyGame) -> str: ...

    @abstractmethod
    def get(self, game_id: str) -> AnyGame | None: ...

    @abstractmethod
    def list(self) -> list[GameSummary]: ...

    @abstractmethod
    def remove(self, game_id: str) -> bool: ...

class MemoryGameStore(GameStoreBase):
    """Current implementation - in-memory"""

class SQLiteGameStore(GameStoreBase):
    """Future implementation - persistent"""
```

**Priority**: Low (MVP is fine with in-memory)
**Effort**: Medium

---

## 4. Testing Improvements

### 4.1 Missing Backend Tests

| Module | Gap | Priority |
|--------|-----|----------|
| `app/plugins/iesds.py` | No tests | High |
| `app/plugins/verify_profile.py` | No tests | Medium |
| `app/conversions/efg_nfg.py` | No tests | High |
| 3+ player games | Limited coverage | Medium |

### 4.2 Frontend Test Setup

```bash
# Add to frontend/package.json
{
  "devDependencies": {
    "vitest": "^1.0.0",
    "@testing-library/react": "^14.0.0"
  },
  "scripts": {
    "test": "vitest"
  }
}
```

**Priority test files**:
1. `frontend/src/canvas/layout/treeLayout.test.ts`
2. `frontend/src/canvas/layout/matrixLayout.test.ts`
3. `frontend/src/types/game.test.ts` (type guards)

---

## 5. Feature Roadmap

### 5.1 Near-term (Next Release)

| Feature | Description | Effort |
|---------|-------------|--------|
| **Task cancellation** | Cancel long-running analyses | Medium |
| **IESDS plugin tests** | Add missing test coverage | Small |
| **Conversion tests** | Add tests for efg_nfg conversions | Small |
| **Error sanitization** | Clean up error messages | Small |

### 5.2 Medium-term

| Feature | Description | Effort |
|---------|-------------|--------|
| **Async task system** | Full task management (Section 3.1) | Large |
| **Frontend tests** | Vitest setup + layout tests | Medium |
| **Keyboard shortcuts** | T for tree, M for matrix, etc. | Small |
| **Game editing** | Modify games in the UI | Large |

### 5.3 Long-term

| Feature | Description | Effort |
|---------|-------------|--------|
| **MAID support** | Multi-agent influence diagrams | Large |
| **Persistence** | SQLite game storage | Medium |
| **Multi-user** | User accounts, saved games | Large |
| **Export** | Download games in various formats | Medium |
| **Simulation** | Run game simulations with strategies | Large |

---

## 6. Technical Debt

### Code Quality

| Item | Location | Notes |
|------|----------|-------|
| DFS vs BFS naming | `app/models/game.py:reachable_outcomes` | Uses `.pop()` (DFS) but named "reachable" |
| Duplicate render logic | `useCanvas.ts` | Tree and matrix render have similar structure |
| Magic numbers | Various | Some layout values not in config |

### Documentation

| Item | Status |
|------|--------|
| API documentation | None (OpenAPI auto-generated) |
| Plugin authoring guide | None |
| Game format specifications | Partial (relies on Gambit docs) |
| Architecture overview | This document |

---

## 7. Release Checklist

Before each release:

- [ ] All tests pass: `.venv/Scripts/python -m pytest tests/ -v`
- [ ] Frontend builds: `cd frontend && npm run build`
- [ ] No TypeScript errors: `cd frontend && npx tsc --noEmit`
- [ ] Example games load correctly
- [ ] Analysis plugins run without errors
- [ ] Manual test: upload game, run analysis, view results

---

## Appendix A: File Structure Reference

```
thrones/
├── app/
│   ├── main.py                 # FastAPI app, endpoints
│   ├── models/                 # Game, NormalFormGame, etc.
│   ├── core/                   # GameStore, Registry
│   ├── formats/                # EFG, NFG, JSON parsers
│   ├── conversions/            # EFG ↔ NFG conversion
│   └── plugins/                # Nash, Dominance, IESDS, Validation
├── frontend/
│   └── src/
│       ├── canvas/             # Pixi.js rendering
│       ├── components/         # React components
│       ├── stores/             # Zustand state
│       └── types/              # TypeScript interfaces
├── tests/                      # Python tests
├── examples/                   # Sample game files
└── docs/                       # Documentation
```

## Appendix B: Dependency Versions

**Backend**:
- Python 3.12+
- FastAPI 0.110.0
- Pydantic 2.6.4
- pygambit 16.4.1
- NumPy 2.4.0

**Frontend**:
- React 19.2.0
- Pixi.js 8.14.3
- Zustand 5.0.9
- TypeScript 5.9.3
- Vite 7.3.0
