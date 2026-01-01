# Agent Guidelines for this repository
- Target Python 3.12+; prefer built-in generics (e.g., `list[str]`) over `typing.List`.
- Favor type safety and local reasoning: keep functions small, type-annotated, and avoid implicit mutations.
- Prefer immutable data where practical (e.g., frozen Pydantic models or dataclasses for configs); avoid shared mutable defaults.
- Stay idiomatic: match existing FastAPI/Pydantic style and keep dependencies minimal.
- Keep plugin discovery automatic (no manual imports) and document runtime dependencies when relevant.
- Testing notes: prefer `python3.12 -m compileall app` and minimal quick checks over long-running suites.
- PR/final messages should summarize changes succinctly and list executed tests.
