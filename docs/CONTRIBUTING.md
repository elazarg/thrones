# Contributing

Thank you for your interest in contributing to the Game Theory Workbench.

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/thrones.git
cd thrones
```

### 2. Set Up Development Environment

**Backend**:
```bash
# Create virtual environment
py -3.12 -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Unix)
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

**Frontend**:
```bash
cd frontend
npm install
```

**Plugins** (optional, for integration tests):
```powershell
# Windows
scripts/setup-plugins.ps1

# Unix
scripts/setup-plugins.sh
```

### 3. Verify Setup

```bash
# Run backend tests
.venv/Scripts/python -m pytest tests/ -v --ignore=tests/integration

# Run frontend build
cd frontend && npm run build
```

---

## Development Workflow

### Branch Naming

Use descriptive branch names:
- `feature/add-xyz-analysis` - New features
- `fix/nash-timeout-handling` - Bug fixes
- `docs/update-plugin-guide` - Documentation
- `refactor/simplify-task-manager` - Refactoring

### Making Changes

1. Create a branch from `main`
2. Make your changes
3. Add/update tests as needed
4. Ensure all tests pass
5. Submit a pull request

### Commit Messages

Write clear, concise commit messages:

```
Add Nash equilibrium solver configuration

- Support solver selection (exhaustive, quick, pure, logit)
- Add max_equilibria limit parameter
- Update API documentation
```

Guidelines:
- Use imperative mood ("Add" not "Added")
- First line: summary under 72 characters
- Body: explain what and why (not how)
- Reference issues if applicable: "Fixes #123"

---

## Code Standards

### Python (Backend)

- **Python 3.12+**: Use modern features (built-in generics, match statements)
- **Type hints**: All public functions should have type annotations
- **Pydantic**: Use for data validation and serialization
- **Async**: Prefer async for I/O-bound operations

Example:
```python
from __future__ import annotations
from pydantic import BaseModel

class GameConfig(BaseModel):
    max_players: int = 4
    timeout_seconds: float = 30.0

async def analyze_game(game_id: str, config: GameConfig | None = None) -> AnalysisResult:
    """Analyze a game and return results.

    Args:
        game_id: The game identifier
        config: Optional analysis configuration

    Returns:
        Analysis results including equilibria found
    """
    ...
```

### TypeScript (Frontend)

- **Strict mode**: TypeScript strict mode is enabled
- **React 18**: Use hooks and functional components
- **Zustand**: For state management
- **No `any`**: Avoid `any` type; use proper interfaces

Example:
```typescript
interface GameState {
  games: Map<string, Game>;
  selectedId: string | null;
}

const useGameStore = create<GameState>((set) => ({
  games: new Map(),
  selectedId: null,
  selectGame: (id: string) => set({ selectedId: id }),
}));
```

### Style Guidelines

- Keep functions small and focused
- Prefer immutable data structures
- Avoid shared mutable state
- Match existing code style in the file

---

## Testing Requirements

### Backend Tests

```bash
# Main app tests (must pass)
.venv/Scripts/python -m pytest tests/ -v --tb=short --ignore=tests/integration

# Plugin tests (if modifying plugins)
plugins/gambit/.venv/Scripts/python -m pytest plugins/gambit/tests/ -v
plugins/pycid/.venv/Scripts/python -m pytest plugins/pycid/tests/ -v

# Integration tests (requires plugin venvs)
.venv/Scripts/python -m pytest tests/integration/ -v --tb=short
```

### Frontend Tests

```bash
cd frontend
npm run build  # Includes TypeScript check
npm test       # If tests exist
```

### Test Guidelines

1. **Unit tests**: Test individual functions/classes in isolation
2. **Integration tests**: Test component interactions
3. **Edge cases**: Cover error conditions and boundary cases
4. **Fixtures**: Use pytest fixtures for reusable test data

Example test:
```python
import pytest
from app.models import ExtensiveFormGame

@pytest.fixture
def simple_game() -> ExtensiveFormGame:
    return ExtensiveFormGame(
        id="test",
        title="Test Game",
        players=["A", "B"],
        root="n1",
        nodes={"n1": ...},
        outcomes={"o1": ...},
    )

def test_game_has_correct_players(simple_game: ExtensiveFormGame):
    assert simple_game.players == ["A", "B"]

def test_validation_catches_missing_root():
    with pytest.raises(ValueError):
        ExtensiveFormGame(root="nonexistent", ...)
```

---

## Documentation

### When to Update Docs

- New features: Add to relevant doc files
- API changes: Update `API_REFERENCE.md`
- New plugins: Add to `PLUGIN_GUIDE.md`
- New formats: Add to `GAME_FORMATS.md`
- Architecture changes: Update `ARCHITECTURE.md`

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Project overview, quick start |
| `docs/ARCHITECTURE.md` | System design |
| `docs/PLUGIN_GUIDE.md` | Plugin development |
| `docs/API_REFERENCE.md` | REST API |
| `docs/GAME_FORMATS.md` | File format specs |
| `docs/TROUBLESHOOTING.md` | Common issues |
| `docs/ROADMAP.md` | Future plans |

---

## Plugin Contributions

See [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) for detailed instructions.

### Quick Checklist

1. Decide: local plugin (in-process) or remote plugin (isolated)?
2. Implement the required interface (`AnalysisPlugin` or HTTP contract)
3. Add tests for your analysis logic
4. Update `plugins.toml` if remote
5. Document configuration options

---

## Pull Request Process

### Before Submitting

- [ ] All tests pass locally
- [ ] Frontend builds without errors
- [ ] Code follows project style
- [ ] Documentation updated (if needed)
- [ ] Commit messages are clear

### PR Template

```markdown
## Summary
Brief description of changes

## Changes
- Change 1
- Change 2

## Testing
- [ ] Added unit tests
- [ ] All tests pass
- [ ] Manual testing performed

## Related Issues
Fixes #123 (if applicable)
```

### Review Process

1. Submit PR against `main`
2. Automated checks run (tests, linting)
3. Maintainer reviews code
4. Address feedback if any
5. Merge when approved

---

## Getting Help

- **Issues**: Report bugs or request features via GitHub Issues
- **Discussions**: Ask questions in GitHub Discussions
- **Code questions**: Add comments in your PR for specific questions

---

## Code of Conduct

- Be respectful and constructive
- Focus on the technical merits
- Welcome newcomers and help them learn
- Assume good intentions
