# Claude Code Project Notes

Instructions for Claude Code when working on this project.

## Python Environment

This project uses a virtual environment at `.venv/`. Always use it:

```bash
# Run Python commands through the venv
.venv/Scripts/python -m pytest tests/ -v
.venv/Scripts/pip install -e ".[dev]"

# Or activate first (Windows)
.venv\Scripts\activate

# Or activate first (Unix)
source .venv/bin/activate
```

**NEVER** use system Python or `pip install` directly. Always use `.venv/Scripts/pip`.

Important: use correct slashes - usually "/" is the right one.

## Dependency Management

### Python (Backend)

Dependencies are defined in `pyproject.toml`:
- Runtime deps in `[project.dependencies]`
- Dev deps in `[project.optional-dependencies.dev]`

To add a new dependency:
1. Add it to `pyproject.toml` first
2. Then install: `.venv/Scripts/pip install -e ".[dev]"`

**NEVER** run `pip install <package>` directly without adding to pyproject.toml first.

### JavaScript (Frontend)

Dependencies are defined in `frontend/package.json`.

To add a new dependency:
1. Add it to `package.json` under `dependencies` or `devDependencies`
2. Use `"latest"` if unsure of version, then lock to resolved version
3. Run `npm install` from the `frontend/` directory

**NEVER** run `npm install <package>` directly without adding to package.json first.

## Running Tests

```bash
# Main app tests (140 pass, 0 skipped)
.venv/Scripts/python -m pytest tests/ -v --tb=short --ignore=tests/integration

# Gambit plugin tests (76 tests, run from plugin venv)
plugins/gambit/.venv/Scripts/python -m pytest plugins/gambit/tests/ -v

# PyCID plugin tests (run from plugin venv)
plugins/pycid/.venv/Scripts/python -m pytest plugins/pycid/tests/ -v

# Integration tests (requires plugin venvs; plugins start automatically)
.venv/Scripts/python -m pytest tests/integration/ -v --tb=short

# All test suites (Windows)
scripts/run-all-tests.ps1

# Frontend build (includes TypeScript check)
cd frontend && npm run build
```

Tests for pygambit-dependent analysis (Nash, IESDS, profile verification, EFG/NFG
parsing) live in `plugins/gambit/tests/` and run in the gambit plugin venv.
Integration tests in `tests/integration/` verify the full main app → plugin HTTP flow.

## Plugin Architecture

Analysis plugins (Gambit, PyCID) run as isolated FastAPI subprocesses, each in its
own virtual environment. This avoids dependency conflicts (e.g. PyCID needs
`pgmpy==0.1.17` + `pygambit>=16.3.2`, while Gambit analyses use `pygambit==16.5.0`).

### Setting Up Plugin Venvs

```bash
# Windows
scripts/setup-plugins.ps1

# Unix
scripts/setup-plugins.sh
```

This creates `plugins/gambit/.venv/` and `plugins/pycid/.venv/` with their respective
dependencies. Plugin venvs are gitignored.

### How It Works

- `plugins.toml` defines plugin subprocess commands, working directories, and restart policies
- On app startup, `PluginManager` launches each plugin on a dynamic port via `subprocess.Popen`
- Each plugin exposes `GET /health`, `GET /info`, `POST /analyze`, `POST /parse/{format}`, `GET /tasks/{id}`, `POST /cancel/{id}`
- `RemotePlugin` adapter makes HTTP plugins look like local `AnalysisPlugin` instances
- Plugins that advertise format support (e.g. `.efg`, `.nfg`) get registered as format parsers via `app/formats/remote.py`
- If a plugin isn't running, its analyses and formats are unavailable (graceful degradation)

### Plugin HTTP Contract

See `plugins.toml` for configuration. Each plugin is a FastAPI app implementing API v1.

## Starting the App

```bash
# Backend (plugins start automatically if venvs are set up)
.venv/Scripts/python -m uvicorn app.main:app --reload

# Frontend dev server
cd frontend && npm run dev
```

## Project Structure

- `app/` - FastAPI backend (thin orchestrator)
- `app/formats/` - Format registry and JSON parser; gambit formats registered dynamically from plugin
- `app/formats/remote.py` - Proxy format parsing to remote plugins via HTTP
- `app/plugins/` - Local plugins (validation, dominance) — no external deps
- `app/core/plugin_manager.py` - Subprocess supervisor for remote plugins
- `app/core/remote_plugin.py` - HTTP adapter for remote plugins
- `plugins/gambit/` - Gambit plugin service (pygambit, own venv)
- `plugins/pycid/` - PyCID plugin service (pycid, pgmpy, own venv)
- `plugins.toml` - Plugin configuration
- `frontend/` - React + Pixi.js frontend
- `tests/` - Python tests (main app, 140 tests)
- `tests/integration/` - Integration tests (main app + plugins, 8 tests)
- `examples/` - Sample game files (.efg, .nfg, .json)
- `scripts/` - Setup and utility scripts
