# Game Theory Workbench - Roadmap

Planned features and improvements.

**Last Updated**: January 2026

---

## Outstanding Issues

### Frontend Test Coverage

**Problem**: No tests for frontend logic, particularly the layout algorithms.

**High-value test targets**:
- `frontend/src/canvas/layout/treeLayout.ts` - Pure function, easy to test
- `frontend/src/canvas/layout/matrixLayout.ts` - Pure function, easy to test
- `frontend/src/stores/*.ts` - State management logic

**Fix**: Add Vitest with tests for layout functions.

### API Case Convention

**Problem**: Backend uses `snake_case`, frontend receives as-is. JavaScript convention is `camelCase`.

**Options**:
1. **Pydantic alias_generator** - Transform on serialization
2. **Frontend transformation** - Transform on receipt
3. **Accept as-is** - Current approach, works but unconventional

### Code Quality

| Item | Location |
|------|----------|
| Duplicate render logic | `useCanvas.ts` - Tree and matrix render have similar structure |
| Magic numbers | Various - Some layout values not in config |

---

## Planned Features

### Near-term

| Feature | Description |
|---------|-------------|
| **Frontend tests** | Vitest setup + layout tests |
| **Keyboard shortcuts** | T for tree, M for matrix, etc. |
| **Progress reporting** | Show analysis progress in UI |

### Medium-term

| Feature | Description |
|---------|-------------|
| **Game editing** | Modify games in the UI |
| **Export** | Download games in various formats |
| **WebSocket updates** | Real-time task status (replace polling) |

### Long-term

| Feature | Description |
|---------|-------------|
| **Persistence** | SQLite game storage |
| **Multi-user** | User accounts, saved games |
| **Simulation** | Run game simulations with strategies |

---

## Potential Plugins

See [potential-plugins.md](potential-plugins.md) for libraries that could be wrapped:

* **Axelrod** - Iterated Prisoner's Dilemma research
* **Nashpy** - Lightweight 2-player matrix game solvers
* **pyAgrum** - Influence diagrams, LIMID solving
* **GameTheory.jl** - N-player normal-form (Julia)

---

## Release Checklist

Before each release:

- [ ] All tests pass: `.venv/Scripts/python -m pytest tests/ -v`
- [ ] Frontend builds: `cd frontend && npm run build`
- [ ] No TypeScript errors: `cd frontend && npx tsc --noEmit`
- [ ] Example games load correctly
- [ ] Analysis plugins run without errors
- [ ] Manual test: upload game, run analysis, view results
