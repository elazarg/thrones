# Architecture Overview

This document describes the system architecture of the Game Theory Workbench.

## System Diagram

```
                        +-----------------------+
                        |       Frontend        |
                        | React + Pixi.js +     |
                        | Zustand + TypeScript  |
                        +-----------+-----------+
                                    |
                                HTTP/REST
                                    |
                        +-----------+-----------+
                        |       Backend         |
                        |   FastAPI (Python)    |
                        |   Orchestration Layer |
                        +-----------+-----------+
                                    |
              +---------------------+---------------------+
              |                     |                     |
    +---------+---------+ +---------+---------+ +---------+---------+
    |   Local Plugins   | |   Remote Plugins  | |   Remote Plugins  |
    | (app/plugins/)    | |  (Gambit service) | |  (PyCID service)  |
    | Validation,       | |  Nash, IESDS,     | |  MAID Nash,       |
    | Dominance         | |  EFG/NFG parsing  | |  Strategic rel.   |
    +-------------------+ +---------+---------+ +---------+---------+
                                    |                     |
                            subprocess             subprocess
                            (own venv)             (own venv)
```

## Component Responsibilities

### Frontend (`frontend/`)

React 18 application with TypeScript, using:
- **Pixi.js 8**: WebGL-accelerated canvas for game tree and matrix visualization
- **Zustand 5**: Lightweight state management for games, analyses, and UI state
- **Vite**: Build tooling and dev server

Key directories:
- `src/canvas/` - Pixi.js rendering, layout algorithms, overlays
- `src/components/` - React UI components (panels, headers, controls)
- `src/stores/` - Zustand state stores (game, analysis, UI)
- `src/types/` - TypeScript interfaces matching backend models

### Backend (`app/`)

FastAPI application serving as a thin orchestration layer:
- **Routes** (`app/routes/`): REST API endpoints for games, tasks, analyses
- **Models** (`app/models/`): Pydantic models for ExtensiveFormGame, NormalFormGame, MAIDGame
- **Formats** (`app/formats/`): Format registry, JSON parser, remote format proxying
- **Core** (`app/core/`): GameStore, TaskManager, PluginManager, Registry

The backend does not contain analysis algorithms directly. It delegates to plugins.

### Local Plugins (`app/plugins/`)

Simple Python modules that run in-process. No external dependencies beyond the main app.

| Plugin | Purpose |
|--------|---------|
| `validation.py` | Structure checks (orphan nodes, missing payoffs) |
| `dominance.py` | Strict/weak dominance detection |

Local plugins register by calling `get_registry().register_analysis(...)` at import time.

### Remote Plugins (`plugins/`)

Isolated FastAPI services running as subprocesses, each with its own virtual environment. This architecture solves dependency conflicts (e.g., PyCID needs `pygambit==16.0.2` while main analyses use `pygambit==16.5.0`).

| Plugin | Location | Dependencies |
|--------|----------|--------------|
| Gambit | `plugins/gambit/` | pygambit 16.5.0 |
| PyCID | `plugins/pycid/` | pycid, pgmpy 0.1.17, pygambit 16.3.2+ |

Remote plugins communicate via HTTP and implement a standardized API (see [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md)).

## Data Flow

### Game Upload Flow

```
1. User uploads file (.efg, .nfg, .json)
         |
         v
2. Backend receives file (POST /api/games/upload)
         |
         v
3. Format detection based on extension/content
         |
         +---> JSON: parsed locally by app/formats/json_format.py
         |
         +---> EFG/NFG: proxied to Gambit plugin via HTTP
                        (POST /parse/efg or /parse/nfg)
         |
         v
4. Game stored in GameStore (in-memory)
         |
         v
5. Game returned to frontend
```

### Analysis Flow

```
1. Frontend submits analysis (POST /api/tasks)
         |
         v
2. Backend looks up plugin in Registry
         |
         v
3. Check if plugin can run on game's native format
         |
         +---> Yes: use native game
         |
         +---> No: try converting to formats in plugin.applicable_to
               (uses cached conversions if available)
         |
         v
4. Execute analysis
         |
         +---> Local plugin: run in ThreadPoolExecutor
         |
         +---> Remote plugin: proxy via HTTP (POST /analyze)
         |
         v
5. Task tracked by TaskManager (pending -> running -> completed)
         |
         v
6. Frontend polls (GET /api/tasks/{id}) until complete
         |
         v
7. Results rendered as canvas overlays
```

**Conversion Fallback**: When a plugin cannot run on the game's native format (e.g., Nash equilibrium on a MAID), the backend automatically attempts to convert the game to formats the plugin supports. The first successful conversion is used. This happens transparently to the client.

## Key Design Decisions

### 1. Subprocess Isolation for Plugins

**Problem**: PyCID and main Gambit analyses have incompatible pygambit versions.

**Solution**: Each plugin runs in its own subprocess with its own Python virtual environment. The main app launches plugins on startup via `PluginManager` and communicates via HTTP.

**Benefits**:
- Complete dependency isolation
- Plugins can crash without affecting the main app
- Easy to add new plugins with arbitrary dependencies

### 2. Dynamic Port Allocation

**Problem**: Multiple plugins need unique ports; hardcoded ports cause collisions.

**Solution**: `PluginManager` allocates ephemeral ports and passes them to plugin subprocesses via command-line arguments.

### 3. Task-Based Async Analysis

**Problem**: Nash equilibrium computation can take seconds to minutes.

**Solution**: Analyses run asynchronously:
1. `POST /api/tasks` returns immediately with `task_id`
2. Client polls `GET /api/tasks/{id}` for status
3. Task states: `pending` -> `running` -> `completed` (or `failed`/`cancelled`)

This keeps HTTP requests fast and supports cancellation.

### 4. Format-Agnostic Canvas

**Problem**: Different game types (tree, matrix, DAG) need different visualizations.

**Solution**: The canvas module is format-agnostic:
- `TreeRenderer` handles extensive-form games
- `MatrixRenderer` handles normal-form games
- Future: `DAGRenderer` for MAIDs

Layout is computed separately from rendering, allowing different layouts for the same game type.

## Directory Structure

```
thrones/
├── app/                      # FastAPI backend
│   ├── main.py               # App entry point, lifespan hooks
│   ├── routes/               # API endpoints
│   │   ├── games.py          # /api/games/*
│   │   ├── tasks.py          # /api/tasks/*
│   │   └── analyses.py       # /api/analyses/*
│   ├── models/               # Pydantic models
│   │   ├── extensive_form.py # ExtensiveFormGame
│   │   ├── normal_form.py    # NormalFormGame
│   │   └── maid.py           # MAIDGame
│   ├── core/                 # Core services
│   │   ├── store.py          # GameStore (in-memory)
│   │   ├── registry.py       # Plugin registry
│   │   ├── tasks.py          # TaskManager
│   │   ├── plugin_manager.py # Remote plugin supervisor
│   │   └── remote_plugin.py  # HTTP adapter for remote plugins
│   ├── formats/              # Format handling
│   │   ├── json_format.py    # JSON parser
│   │   └── remote.py         # Proxy to remote format parsers
│   ├── plugins/              # Local plugins
│   │   ├── validation.py
│   │   └── dominance.py
│   └── conversions/          # Format conversions
│       └── efg_nfg.py        # EFG <-> NFG
│
├── plugins/                  # Remote plugin services
│   ├── gambit/               # Gambit plugin
│   │   ├── gambit_plugin/    # Python package
│   │   ├── pyproject.toml    # Dependencies
│   │   └── tests/            # Plugin tests
│   └── pycid/                # PyCID plugin
│       ├── pycid_plugin/
│       ├── pyproject.toml
│       └── tests/
│
├── frontend/                 # React + Pixi.js frontend
│   └── src/
│       ├── canvas/           # Pixi.js rendering
│       │   ├── layout/       # Tree/matrix layout algorithms
│       │   ├── renderers/    # Visual element renderers
│       │   └── overlays/     # Analysis result overlays
│       ├── components/       # React components
│       ├── stores/           # Zustand stores
│       ├── lib/              # Utilities (API client)
│       └── types/            # TypeScript interfaces
│
├── tests/                    # Backend tests
│   ├── integration/          # Main app + plugin tests
│   └── ...
│
├── examples/                 # Sample game files
├── scripts/                  # Setup and utility scripts
├── plugins.toml              # Plugin configuration
└── docs/                     # Documentation
```

## Related Documentation

- [Canvas Architecture](canvas-architecture.md) - Frontend canvas layers and rendering
- [Tech Stack](gambit-tech-stack.md) - Technology choices and rationale
- [Plugin Guide](PLUGIN_GUIDE.md) - How to create plugins
- [Design Philosophy](gambit-canvas-design.md) - Product vision and design principles
