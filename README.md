# Game Theory Workbench MVP

A canvas-first game theory analysis and visualization workbench. See `design/` for the full design vision.

## Architecture

- **Backend**: FastAPI + Python 3.12 with plugin-based analysis system
- **Frontend**: React 18 + TypeScript + Pixi.js 8 for canvas rendering
- **Analysis**: Nash equilibrium via pygambit, extensible plugin registry

## Quick Start

### Backend

```bash
# Create and activate virtual environment
py -3.12 -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# Install dependencies (pygambit may take a few minutes to build)
pip install -e ".[dev]"

# Run the server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev  # Development server at http://localhost:5173
```

The Vite dev server proxies `/api` requests to the backend at port 8000.

### Production Build

```bash
cd frontend
npm run build  # Outputs to frontend/dist
# Backend serves frontend/dist when it exists
uvicorn app.main:app --port 8000
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=term-missing
```

## Project Structure

```
app/                    # FastAPI backend
  main.py               # App entry, Trust Game, API endpoints
  models/game.py        # Pydantic models: Game, DecisionNode, etc.
  core/registry.py      # Plugin registry system
  plugins/              # Analysis plugins (auto-discovered)
    nash.py             # Nash equilibrium via pygambit

frontend/               # React + Pixi.js frontend
  src/
    components/         # React components
      canvas/           # Pixi.js game tree visualization
      layout/           # Header, StatusBar, MainLayout
      panels/           # AnalysisPanel
    stores/             # Zustand state management
    types/              # TypeScript types matching Pydantic models
    lib/                # Tree layout algorithm, API client

tests/                  # pytest test suite
design/                 # Design documents and wireframes
```

## Extending

- Add new analyses under `app/plugins/` - they are auto-discovered on startup
- See `design/gambit-canvas-design.md` for the plugin interface specification

## Requirements

- Python 3.12+
- Node.js 18+ (for frontend)
- Rust/Cargo (for building pygambit C++ bindings)

