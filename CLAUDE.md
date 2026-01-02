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
# Backend tests (69 tests)
.venv/Scripts/python -m pytest tests/ -v --tb=short

# Frontend build (includes TypeScript check)
cd frontend && npm run build
```

## Starting the App

```bash
# Backend
.venv/Scripts/python -m uvicorn app.main:app --reload

# Frontend dev server
cd frontend && npm run dev
```

## Project Structure

- `app/` - FastAPI backend
- `frontend/` - React + Pixi.js frontend
- `tests/` - Python tests
- `examples/` - Sample game files (.efg, .nfg, .json)
- `scripts/` - Utility scripts (restart.sh, restart.ps1)
