# Agent Guidelines for this repository

## Python Backend
- Target Python 3.12+; prefer built-in generics (e.g., `list[str]`) over `typing.List`.
- Favor type safety and local reasoning: keep functions small, type-annotated, and avoid implicit mutations.
- Prefer immutable data where practical (e.g., frozen Pydantic models or dataclasses for configs); avoid shared mutable defaults.
- Stay idiomatic: match existing FastAPI/Pydantic style and keep dependencies minimal.
- Keep plugin discovery automatic (no manual imports) and document runtime dependencies when relevant.
- Install with `pip install -e ".[dev]"` (uses pyproject.toml).
- Run tests with `pytest tests/ -v`.

## Frontend
- React 18 + TypeScript + Pixi.js 8 for canvas rendering.
- Zustand for state management.
- Run with `cd frontend && npm install && npm run dev`.

## PR/Commit Guidelines
- Summarize changes succinctly and list executed tests.
