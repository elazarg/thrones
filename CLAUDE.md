# Claude Code Project Notes

Instructions for Claude Code when working on this project.

## Docker Development

This project uses Docker Compose to run the backend and plugins. Frontend runs separately via npm.

### Starting the Backend

```bash
# Build all images (first time or after code changes)
docker compose build

# Start all services
docker compose up

# Start in background
docker compose up -d

# View logs
docker compose logs -f app

# Stop all services
docker compose down
```

### Starting the Frontend

```bash
cd frontend
npm install   # first time only
npm run dev   # starts dev server on http://localhost:5173
```

### Rebuilding After Changes

```bash
# Rebuild specific service
docker compose build gambit && docker compose up -d gambit

# Rebuild all services
docker compose build && docker compose up -d
```

### Running Tests

```bash
# Run main app tests inside container
docker compose exec app pytest tests/ -v --tb=short --ignore=tests/integration

# Run integration tests (requires all services running)
docker compose exec app pytest tests/integration/ -v --tb=short

# Frontend tests
npm test --prefix frontend

# Frontend build (includes TypeScript check)
npm run build --prefix frontend
```

### Linting & Code Quality

Install dev dependencies first: `pip install -e ".[dev]"`

```bash
# Backend - run all linters
ruff check app/                              # Linting
ruff format app/                             # Auto-format code
ruff format --check app/                     # Check formatting without changes
mypy app/ --ignore-missing-imports           # Type checking
bandit -r app/ -x app/tests --skip B101      # Security scan

# Frontend
npm run lint --prefix frontend               # TypeScript type check
```

## Plugin Architecture

Analysis plugins (Gambit, PyCID, Vegas, EGTTools, OpenSpiel) run as Docker containers
managed by Docker Compose. This avoids dependency conflicts (e.g., PyCID needs
`pgmpy==0.1.17` + `pygambit>=16.3.2`, while Gambit analyses use `pygambit`).

### How It Works

- `docker-compose.yml` defines all services and their health checks
- `plugins.toml` lists plugin names; URLs come from environment variables
- On app startup, `PluginManager` health-checks each plugin container
- Each plugin exposes `GET /health`, `GET /info`, `POST /analyze`, `POST /parse/{format}`, `GET /tasks/{id}`, `POST /cancel/{id}`
- `RemotePlugin` adapter makes HTTP plugins look like local `AnalysisPlugin` instances
- Plugins that advertise format support (e.g., `.efg`, `.nfg`) get registered as format parsers
- If a plugin container isn't healthy, its analyses and formats are unavailable (graceful degradation)

### Plugin HTTP Contract

Each plugin is a FastAPI app implementing API v1. See individual plugin Dockerfiles in `docker/`.

### Service Ports

| Service    | Internal Port | External Port |
|------------|---------------|---------------|
| Main App   | 8000          | 8000          |
| Gambit     | 5001          | 5001          |
| PyCID      | 5002          | 5002          |
| EGTTools   | 5003          | 5003          |
| Vegas      | 5004          | 5004          |
| OpenSpiel  | 5005          | 5005          |

## Dependency Management

### Python (Backend)

Dependencies are defined in `pyproject.toml` and plugin-specific `pyproject.toml` files.
Docker images install dependencies during build.

To add a new dependency:
1. Add it to the appropriate `pyproject.toml`
2. Rebuild the Docker image: `docker compose build <service>`

### JavaScript (Frontend)

Dependencies are defined in `frontend/package.json`.

To add a new dependency:
1. Add it to `package.json` under `dependencies` or `devDependencies`
2. Run `npm install` from the `frontend/` directory

## Project Structure

- `app/` - FastAPI backend (thin orchestrator)
- `app/formats/` - Format registry and JSON parser; gambit formats registered dynamically from plugin
- `app/formats/remote.py` - Proxy format parsing to remote plugins via HTTP
- `app/plugins/` - Local plugins (validation, dominance) - no external deps
- `app/core/plugin_manager.py` - Plugin discovery and health-checking for Docker containers
- `app/core/remote_plugin.py` - HTTP adapter for remote plugins
- `plugins/gambit/` - Gambit plugin service (pygambit)
- `plugins/pycid/` - PyCID plugin service (pycid, pgmpy)
- `plugins/vegas/` - Vegas DSL plugin service
- `plugins/egttools/` - Evolutionary game theory plugin service
- `plugins/openspiel/` - OpenSpiel plugin service (CFR, exploitability)
- `docker/` - Dockerfiles for all services
- `docker-compose.yml` - Service orchestration
- `plugins.toml` - Plugin configuration (names only; URLs from environment)
- `frontend/` - React + Pixi.js frontend
- `tests/` - Python tests (main app)
- `tests/integration/` - Integration tests (main app + plugins)
- `examples/` - Sample game files (.efg, .nfg, .json)
