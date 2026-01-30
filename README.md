# Game Theory Workbench

A canvas-first game theory analysis and visualization workbench. Build, visualize, and analyze game trees with equilibrium computation.

## Key Features

- **Interactive Canvas**: Drag, zoom, and pan through game trees rendered with Pixi.js
- **Dual Views**: Switch between extensive-form (tree) and normal-form (matrix) representations
- **Async Analysis**: Nash equilibrium, IESDS, and dominance computed via background tasks; UI updates when results arrive
- **Multiple Formats**: Load games from JSON, Gambit EFG, Gambit NFG, and MAID files
- **Format Conversion**: Convert between extensive and normal form on demand (2-player games)
- **Plugin Architecture**: Extend with custom analyses via Python plugins

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- Rust (for building pygambit)

### Backend Setup

```bash
# Create and activate virtual environment
py -3.12 -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Unix

# Install dependencies
pip install -e ".[dev]"

# Set up analysis plugins (Nash equilibrium, IESDS)
scripts/setup-plugins.ps1       # Windows
# scripts/setup-plugins.sh      # Unix

# Start the server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 to access the workbench.

## Project Structure

```
thrones/
├── app/                    # FastAPI backend
│   ├── routes/             # API endpoints
│   ├── models/             # Game data models
│   ├── plugins/            # Local analysis plugins
│   └── core/               # Store, registry, task manager
├── plugins/                # Remote analysis plugins (isolated venvs)
│   ├── gambit/             # Nash, IESDS, EFG/NFG parsing (pygambit)
│   ├── pycid/              # MAID Nash, strategic relevance (pycid)
│   ├── vegas/              # Vegas DSL parsing (.vg files)
│   ├── egttools/           # Evolutionary dynamics (replicator, fixation)
│   └── openspiel/          # CFR, exploitability (Linux/macOS only)
├── frontend/               # React + Pixi.js UI
│   └── src/
│       ├── canvas/         # Game visualization
│       ├── components/     # UI components
│       └── stores/         # State management
├── examples/               # Sample game files
├── tests/                  # Test suites
└── docs/                   # Documentation
```

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System design and plugin architecture |
| [Plugin Guide](docs/PLUGIN_GUIDE.md) | How to create analysis plugins |
| [API Reference](docs/API_REFERENCE.md) | REST API documentation |
| [Game Formats](docs/GAME_FORMATS.md) | JSON, EFG, NFG, Vegas DSL specs |
| [Contributing](docs/CONTRIBUTING.md) | Development workflow |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and solutions |

## Running Tests

```bash
# Backend tests
.venv/Scripts/python -m pytest tests/ -v --ignore=tests/integration

# Plugin tests (run from plugin venv)
plugins/gambit/.venv/Scripts/python -m pytest plugins/gambit/tests/ -v

# Integration tests
.venv/Scripts/python -m pytest tests/integration/ -v

# Frontend build (includes TypeScript check)
cd frontend && npm run build
```

## Example Games

The `examples/` directory contains sample games in various formats:

| File | Format | Description |
|------|--------|-------------|
| `trust-game.json` | Extensive | Classic trust game (sequential) |
| `matching-pennies.json` | Normal | Zero-sum matching game |
| `prisoners-dilemma.json` | Normal | Classic prisoner's dilemma |
| `prisoners-dilemma.vg` | Vegas DSL | Same game in Vegas format |
| `rock-paper-scissors.json` | Normal | RPS with standard payoffs |
| `battle-of-sexes.json` | Normal | Coordination game |
| `stag-hunt.json` | Normal | Stag hunt coordination |
| `centipede.json` | Extensive | Multi-stage centipede game |
| `signaling-game.json` | Extensive | Signaling with imperfect info |
| `MontyHall.efg` | Gambit EFG | Monty Hall problem |

## Technology Stack

- **Backend**: FastAPI, Pydantic
- **Frontend**: React 19, Pixi.js 8, Zustand, TypeScript
- **Analysis Plugins**:
  - **Gambit**: Nash equilibrium, IESDS, EFG/NFG parsing (pygambit)
  - **PyCID**: MAID Nash equilibrium, strategic relevance analysis (pycid)
  - **Vegas**: Vegas DSL game description language
  - **EGTTools**: Evolutionary dynamics, replicator equations, fixation probabilities
  - **OpenSpiel**: CFR, exploitability (Linux/macOS only)

## Current Version

**v0.5.0** - Plugin ecosystem with 5 remote analysis plugins.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
