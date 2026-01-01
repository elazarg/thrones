# Game Theory Workbench: Technology Stack

## Design Constraints

Before choosing technologies, establish what we're optimizing for:

1. **Researcher extensibility**: Plugins will be written by game theorists, not web developers. They know Python, maybe R, possibly Julia. Not TypeScript.

2. **Interop with existing tools**: Must call Gambit CLI, integrate with pygambit, potentially nashpy, Gambit's Python bindings, external solvers.

3. **Rich canvas interaction**: Game trees need drag-drop, zoom, pan, animation. Not a simple DOM problem.

4. **Live updates**: Analyses run continuously; results stream back. WebSocket-style reactivity.

5. **Cross-platform**: Researchers use macOS, Windows, Linux. Can't assume any one.

6. **Proven practice**: No bleeding-edge frameworks. Things that will exist in 5 years.

7. **Packageable**: Must work as a standalone app, not require users to install Python/Node separately.

---

## Architecture Options

### Option A: Pure Web (Electron)

```
┌─────────────────────────────────────────────────────┐
│                    Electron                         │
│  ┌───────────────────────────────────────────────┐ │
│  │              React + TypeScript               │ │
│  │  ┌─────────────┐  ┌─────────────────────────┐│ │
│  │  │   Canvas    │  │    State Management    ││ │
│  │  │  (Pixi.js)  │  │      (Zustand)         ││ │
│  │  └─────────────┘  └─────────────────────────┘│ │
│  └───────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────┐ │
│  │              Node.js Backend                  │ │
│  │  • Gambit CLI calls (child_process)          │ │
│  │  • File system                                │ │
│  │  • Plugin loading                             │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Pros:**
- Single language (TypeScript) for UI and logic
- Mature ecosystem, proven at scale (VS Code, Slack, Discord)
- Good canvas libraries (Pixi.js, Konva)
- Cross-platform out of the box

**Cons:**
- Plugins in TypeScript—researchers won't write them
- Heavy runtime (~150MB minimum)
- Calling Python libraries requires subprocess or embedding
- Node ecosystem churn

**Verdict**: Rejects constraint #1 (researcher extensibility). Researchers won't write TypeScript plugins.

---

### Option B: Python Desktop (Qt)

```
┌─────────────────────────────────────────────────────┐
│                   PyQt6 / PySide6                   │
│  ┌───────────────────────────────────────────────┐ │
│  │              QGraphicsView                     │ │
│  │           (Canvas for game trees)             │ │
│  └───────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────┐ │
│  │              Python Core                       │ │
│  │  • pygambit integration                       │ │
│  │  • Plugin system (entry points)              │ │
│  │  • Analysis engine                            │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Pros:**
- Pure Python—researchers can extend everything
- Qt is battle-tested (30+ years)
- QGraphicsView is capable for 2D graphics
- Direct pygambit/numpy integration
- PyInstaller/Nuitka for packaging

**Cons:**
- Qt has a learning curve
- QGraphicsView is powerful but verbose
- UI looks dated without significant effort
- Licensing complexity (GPL vs commercial)

**Verdict**: Viable. Prioritizes extensibility over UI polish. Consider seriously.

---

### Option C: Python + Web Hybrid

```
┌─────────────────────────────────────────────────────┐
│                   Tauri Shell                       │
│  ┌───────────────────────────────────────────────┐ │
│  │              React + TypeScript               │ │
│  │         (UI only—no business logic)          │ │
│  │  ┌─────────────────────────────────────────┐ │ │
│  │  │            Canvas (Pixi.js)             │ │ │
│  │  └─────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────┘ │
│                        │                            │
│                   WebSocket                         │
│                        │                            │
│  ┌───────────────────────────────────────────────┐ │
│  │              Python Backend                    │ │
│  │  ┌─────────────┐  ┌─────────────────────────┐│ │
│  │  │  FastAPI    │  │    Plugin System        ││ │
│  │  │  (async)    │  │   (entry points)        ││ │
│  │  └─────────────┘  └─────────────────────────┘│ │
│  │  ┌─────────────┐  ┌─────────────────────────┐│ │
│  │  │  pygambit   │  │   Analysis Engine       ││ │
│  │  └─────────────┘  └─────────────────────────┘│ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Pros:**
- Python for all logic and plugins—researchers extend in Python
- Web for UI—modern, flexible, good canvas support
- Clear separation: UI is "dumb", Python is "smart"
- Tauri is lightweight (~10MB vs Electron's 150MB)
- FastAPI + WebSocket = excellent real-time support

**Cons:**
- Two languages, two build systems
- Communication overhead (serialization)
- More complex deployment (bundle Python runtime)
- UI developers and plugin developers work in different languages

**Verdict**: Best balance. UI people use TypeScript, researchers use Python. Clear boundary.

---

### Option D: Python + Jupyter Integration

```
┌─────────────────────────────────────────────────────┐
│                  JupyterLab                         │
│  ┌───────────────────────────────────────────────┐ │
│  │           Custom JupyterLab Extension         │ │
│  │              (TypeScript)                     │ │
│  └───────────────────────────────────────────────┘ │
│                        │                            │
│  ┌───────────────────────────────────────────────┐ │
│  │              ipywidgets / anywidget           │ │
│  │           (Canvas embedded in notebook)       │ │
│  └───────────────────────────────────────────────┘ │
│                        │                            │
│  ┌───────────────────────────────────────────────┐ │
│  │              Python Kernel                     │ │
│  │  (All logic lives here, interactively)        │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Pros:**
- Researchers already use Jupyter
- Interactive exploration is natural
- Python-first
- No packaging problem (they already have Jupyter)

**Cons:**
- JupyterLab extension API is painful
- Notebook paradigm doesn't fit continuous-canvas model well
- Limited UI flexibility
- Version conflicts with user's existing Jupyter

**Verdict**: Good for a lightweight widget library (like `ipygambit`), not for the full workbench. Could be complementary.

---

### Option E: Tauri + Rust Core + Python Plugins

```
┌─────────────────────────────────────────────────────┐
│                   Tauri Shell                       │
│  ┌───────────────────────────────────────────────┐ │
│  │              React + TypeScript               │ │
│  └───────────────────────────────────────────────┘ │
│                        │                            │
│                    Tauri IPC                        │
│                        │                            │
│  ┌───────────────────────────────────────────────┐ │
│  │              Rust Core                         │ │
│  │  • Game data structures                       │ │
│  │  • Version control                            │ │
│  │  • Plugin host (PyO3 for Python)             │ │
│  └───────────────────────────────────────────────┘ │
│                        │                            │
│                      PyO3                           │
│                        │                            │
│  ┌───────────────────────────────────────────────┐ │
│  │              Python Plugins                    │ │
│  │  (Loaded into embedded Python interpreter)    │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Pros:**
- Rust core = fast, safe, small binary
- Python plugins via PyO3 = researcher-friendly extension
- Tauri = lightweight, modern
- Best performance ceiling

**Cons:**
- Rust has steep learning curve
- PyO3 embedding adds complexity
- Three languages in the stack
- Smaller contributor pool

**Verdict**: Over-engineered for this use case. Rust core doesn't add enough value—game theory computations are in Gambit/Python anyway.

---

## Decision: Option C (Python + Web Hybrid)

**Rationale:**

1. **Researchers write Python plugins.** This is non-negotiable. They know Python, they use pygambit, they won't learn TypeScript.

2. **Web UI is the best canvas platform.** Pixi.js/Canvas API are more capable and better documented than Qt's QGraphicsView. Web tooling is mature.

3. **Clear separation enables parallel development.** UI team works in TypeScript, core team works in Python. Interface is a well-defined WebSocket protocol.

4. **Tauri over Electron.** Same capability, 10x smaller. Rust shell is fast and secure.

5. **Python backend is the "brain".** All game state, analysis, plugins live in Python. The frontend is a view.

---

## Detailed Stack

### Frontend (TypeScript)

```
┌─────────────────────────────────────────────────────────────────────┐
│  FRONTEND                                                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Framework:        React 18+                                        │
│                    (Proven, huge ecosystem, good for complex UI)   │
│                                                                     │
│  Language:         TypeScript 5+                                    │
│                    (Type safety, better tooling)                   │
│                                                                     │
│  Canvas:           Pixi.js 8                                        │
│                    (WebGL-accelerated 2D, handles thousands of     │
│                     nodes, good interaction support)                │
│                                                                     │
│  State:            Zustand                                          │
│                    (Simple, fast, no boilerplate)                  │
│                                                                     │
│  Communication:    Native WebSocket                                 │
│                    + TanStack Query for REST calls                 │
│                                                                     │
│  Build:            Vite                                             │
│                    (Fast, modern, good Tauri integration)          │
│                                                                     │
│  Styling:          Tailwind CSS + Radix UI                         │
│                    (Utility classes + accessible components)       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Why Pixi.js over alternatives:**
- **vs Konva**: Pixi is faster (WebGL), better for large trees
- **vs D3**: D3 is for data viz, not interactive canvases
- **vs raw Canvas**: Pixi handles scene graph, hit testing, transforms
- **vs Three.js**: Overkill, we don't need 3D

### Backend (Python)

```
┌─────────────────────────────────────────────────────────────────────┐
│  BACKEND                                                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Runtime:          Python 3.11+                                     │
│                    (Required for modern async, type hints)         │
│                                                                     │
│  Framework:        FastAPI                                          │
│                    (Async, WebSocket, OpenAPI, Pydantic)           │
│                                                                     │
│  Validation:       Pydantic v2                                      │
│                    (Fast, good for plugin interfaces)              │
│                                                                     │
│  Async:            asyncio + anyio                                  │
│                    (Run analyses concurrently)                     │
│                                                                     │
│  Game Theory:      pygambit (primary)                               │
│                    nashpy (backup/comparison)                      │
│                    subprocess for Gambit CLI                        │
│                                                                     │
│  Plugins:          importlib.metadata (entry points)               │
│                    (Standard Python plugin discovery)              │
│                                                                     │
│  LLM:              anthropic / openai SDK                          │
│                    (For LLM collaborator feature)                  │
│                                                                     │
│  Testing:          pytest + pytest-asyncio                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Why FastAPI:**
- Native async (analyses run concurrently)
- First-class WebSocket support
- Pydantic integration (validation, serialization)
- OpenAPI generation (debugging, testing)
- Large community, good docs

### Shell (Rust/Tauri)

```
┌─────────────────────────────────────────────────────────────────────┐
│  SHELL                                                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Framework:        Tauri 2.0                                        │
│                    (Lightweight, secure, cross-platform)           │
│                                                                     │
│  Python bundling:  PyOxidizer or PyInstaller                       │
│                    (Bundle Python + deps into app)                 │
│                                                                     │
│  Process model:    Tauri spawns Python backend as sidecar          │
│                    Frontend connects via localhost WebSocket        │
│                                                                     │
│  File access:      Tauri APIs (save dialogs, file watching)        │
│                                                                     │
│  Updates:          Tauri updater                                    │
│                    (Built-in auto-update support)                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Why Tauri over Electron:**
- 10-15x smaller binary (~15MB vs ~150MB)
- Lower memory footprint
- Better security model (no Node.js in renderer)
- Rust shell is fast for file operations
- Growing ecosystem, backed by serious funding

---

## Communication Protocol

Frontend and backend communicate via WebSocket with a simple JSON protocol:

```typescript
// Message types
type Message = 
  | { type: "game.update", payload: GameState }
  | { type: "analysis.result", payload: AnalysisResult }
  | { type: "analysis.progress", payload: { id: string, progress: number } }
  | { type: "llm.proposal", payload: LLMProposal }
  | { type: "simulation.step", payload: SimulationStep }
  | { type: "error", payload: { code: string, message: string } }
```

```python
# Python side
@dataclass
class GameUpdate:
    type: Literal["game.update"] = "game.update"
    payload: GameState

async def broadcast(self, message: Message):
    for client in self.clients:
        await client.send_json(message.dict())
```

**REST endpoints for non-realtime operations:**
- `GET /games` - list games
- `POST /games` - create game
- `GET /games/{id}/versions` - version history
- `POST /games/{id}/export` - export to format
- `GET /plugins` - list installed plugins

---

## Plugin System

Plugins are Python packages that register via entry points:

```toml
# pyproject.toml for a plugin
[project]
name = "gtw-maid"
version = "0.1.0"

[project.entry-points."gtw.formats"]
maid = "gtw_maid.format:MAIDFormat"

[project.entry-points."gtw.analyses"]
maid-nash = "gtw_maid.analysis:MAIDNashEquilibrium"

[project.entry-points."gtw.visualizations"]
maid-dag = "gtw_maid.viz:MAIDDagVisualization"
```

```python
# Plugin base classes
from abc import ABC, abstractmethod
from pydantic import BaseModel

class FormatPlugin(ABC):
    """Plugin for supporting a game format."""
    
    name: str
    extensions: list[str]  # e.g., [".maid", ".maid.json"]
    
    @abstractmethod
    def can_load(self, path: Path) -> bool:
        """Check if this format can load the file."""
        
    @abstractmethod
    def load(self, path: Path) -> Game:
        """Load a game from file."""
        
    @abstractmethod
    def save(self, game: Game, path: Path) -> None:
        """Save a game to file."""


class AnalysisPlugin(ABC):
    """Plugin for game analysis."""
    
    name: str
    description: str
    applicable_to: list[str]  # ["extensive", "normal", "maid"]
    continuous: bool  # Run automatically on changes?
    
    @abstractmethod
    def can_run(self, game: Game) -> bool:
        """Check if analysis applies to this game."""
    
    @abstractmethod
    async def run(self, game: Game, config: dict) -> AnalysisResult:
        """Execute the analysis."""
    
    def render_overlay(self, result: AnalysisResult) -> list[CanvasOverlay]:
        """Return visual overlays for the canvas (optional)."""
        return []
    
    def summarize(self, result: AnalysisResult) -> str:
        """One-line summary for status bar."""
        return f"{self.name}: done"


class SimulationPlugin(ABC):
    """Plugin for agent-based simulation."""
    
    name: str
    description: str
    
    @abstractmethod
    async def choose_action(
        self, 
        game: Game, 
        info_set: InfoSet, 
        history: list[Action],
        config: dict
    ) -> tuple[Action, str | None]:
        """Choose an action. Optionally return reasoning."""
```

**Discovery:**

```python
from importlib.metadata import entry_points

def discover_plugins():
    plugins = {
        "formats": [],
        "analyses": [],
        "visualizations": [],
        "simulations": [],
    }
    
    for category in plugins:
        eps = entry_points(group=f"gtw.{category}")
        for ep in eps:
            try:
                cls = ep.load()
                plugins[category].append(cls())
            except Exception as e:
                logger.warning(f"Failed to load plugin {ep.name}: {e}")
    
    return plugins
```

---

## Data Model

Core data structures (Python, serializable via Pydantic):

```python
from pydantic import BaseModel
from typing import Literal
from uuid import UUID
from datetime import datetime

class Player(BaseModel):
    id: str
    name: str
    color: str | None = None

class Action(BaseModel):
    id: str
    label: str

class InfoSet(BaseModel):
    id: str
    player_id: str
    actions: list[Action]
    node_ids: list[str]

class Node(BaseModel):
    id: str
    type: Literal["decision", "chance", "terminal"]
    player_id: str | None  # None for terminal
    info_set_id: str | None  # None for terminal
    parent_id: str | None
    parent_action_id: str | None
    payoffs: dict[str, float] | None  # Only for terminal

class ChanceNode(Node):
    type: Literal["chance"] = "chance"
    probabilities: dict[str, float]  # action_id -> probability

class Game(BaseModel):
    id: UUID
    name: str
    format: str  # "extensive", "normal", "maid", etc.
    players: list[Player]
    nodes: list[Node]  # For extensive form
    matrix: dict | None  # For normal form
    metadata: dict = {}

class GameVersion(BaseModel):
    id: UUID
    game_id: UUID
    version: int
    created_at: datetime
    description: str
    state: Game
    parent_version: int | None  # For branching

class AnalysisResult(BaseModel):
    id: UUID
    analysis_type: str
    game_version_id: UUID
    status: Literal["success", "partial", "failed", "timeout"]
    result: dict  # Analysis-specific
    warnings: list[str]
    computation_time_ms: int
    engine: str  # "gambit-enummixed", "nashpy", etc.

class CanvasOverlay(BaseModel):
    """Visual annotation to render on canvas."""
    type: Literal["edge_weight", "node_marker", "node_style", "label"]
    target_id: str  # Node or edge ID
    value: dict  # Type-specific data
```

---

## File Structure

```
game-theory-workbench/
├── frontend/                    # TypeScript/React
│   ├── src/
│   │   ├── components/
│   │   │   ├── Canvas/         # Pixi.js game canvas
│   │   │   ├── StatusBar/
│   │   │   ├── LLMPrompt/
│   │   │   └── Panels/
│   │   ├── stores/             # Zustand stores
│   │   ├── hooks/              # React hooks
│   │   ├── lib/
│   │   │   ├── ws.ts           # WebSocket client
│   │   │   └── protocol.ts     # Message types
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                     # Python
│   ├── src/gtw/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app
│   │   ├── models/             # Pydantic models
│   │   ├── core/
│   │   │   ├── game.py         # Game logic
│   │   │   ├── version.py      # Version control
│   │   │   └── engine.py       # Analysis orchestration
│   │   ├── plugins/
│   │   │   ├── base.py         # Plugin ABCs
│   │   │   ├── discovery.py    # Entry point loading
│   │   │   └── builtin/        # Built-in plugins
│   │   │       ├── efg.py
│   │   │       ├── nfg.py
│   │   │       ├── nash.py
│   │   │       └── dominance.py
│   │   ├── llm/
│   │   │   ├── client.py       # Anthropic/OpenAI
│   │   │   └── prompts.py
│   │   └── simulation/
│   │       ├── runner.py
│   │       └── agents/
│   ├── tests/
│   ├── pyproject.toml
│   └── requirements.lock
│
├── src-tauri/                   # Rust/Tauri shell
│   ├── src/
│   │   ├── main.rs
│   │   └── sidecar.rs          # Python process management
│   ├── Cargo.toml
│   └── tauri.conf.json
│
├── plugins/                     # Example/official plugins
│   ├── gtw-maid/
│   ├── gtw-qre/
│   └── gtw-llm-agents/
│
└── docs/
    ├── plugin-guide.md
    └── api-reference.md
```

---

## Interoperability

### Gambit Integration

```python
import pygambit as gbt
import subprocess
import asyncio

class GambitEngine:
    """Wrapper for Gambit tools."""
    
    async def solve_enummixed(self, game: Game) -> list[Equilibrium]:
        """Use gambit-enummixed for exact Nash computation."""
        # Convert to EFG format
        efg_content = self.to_efg(game)
        
        # Run solver
        proc = await asyncio.create_subprocess_exec(
            "gambit-enummixed", "-q",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(efg_content.encode())
        
        # Parse output
        return self.parse_equilibria(stdout.decode())
    
    def via_pygambit(self, game: Game) -> gbt.Game:
        """Convert to pygambit object for direct manipulation."""
        g = gbt.Game.new_tree()
        # ... build tree ...
        return g
```

### External Solver Protocol

For solvers that aren't Gambit:

```python
class ExternalSolverPlugin(AnalysisPlugin):
    """Base for external solver integration."""
    
    command: str  # e.g., "lemke-howson-solver"
    input_format: str  # e.g., "nfg", "json"
    output_format: str
    
    async def run(self, game: Game, config: dict) -> AnalysisResult:
        # Serialize game
        input_data = self.serialize(game, self.input_format)
        
        # Call solver
        proc = await asyncio.create_subprocess_exec(
            self.command, *self.build_args(config),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate(input_data)
        
        # Parse result
        return self.parse_output(stdout, self.output_format)
```

### Jupyter Widget (Companion)

A lightweight widget for Jupyter users:

```python
# ipygtw - separate package
import ipywidgets as widgets
from IPython.display import display

class GameWidget(widgets.DOMWidget):
    """Embeddable game theory canvas for Jupyter."""
    
    _view_name = Unicode('GameView').tag(sync=True)
    _model_name = Unicode('GameModel').tag(sync=True)
    game_state = Dict({}).tag(sync=True)
    
    def load(self, game: Game):
        self.game_state = game.dict()
    
    def on_edit(self, callback):
        """Register callback for user edits."""
        self.observe(callback, names=['game_state'])
```

---

## Deployment Configurations

### Desktop App (Primary)

```
┌─────────────────────────────────────────────────────┐
│                   Tauri Bundle                      │
│  ┌───────────────────────────────────────────────┐ │
│  │  Frontend (HTML/JS/CSS)                       │ │
│  └───────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────┐ │
│  │  Python Sidecar (PyOxidizer bundle)          │ │
│  │  • Python 3.11 runtime                        │ │
│  │  • All dependencies                           │ │
│  │  • Gambit binaries                            │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘

Size: ~50-80MB (varies by platform)
```

### Web Hosted (Alternative)

```
┌─────────────────────────────────────────────────────┐
│                   Web Browser                       │
│  ┌───────────────────────────────────────────────┐ │
│  │  Frontend (same as desktop)                   │ │
│  └───────────────────────────────────────────────┘ │
└───────────────────────┬─────────────────────────────┘
                        │ WebSocket
┌───────────────────────┴─────────────────────────────┐
│                   Server                            │
│  ┌───────────────────────────────────────────────┐ │
│  │  Python Backend (Docker)                      │ │
│  │  • Multi-tenant                               │ │
│  │  • Session management                         │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Developer Mode

```bash
# Terminal 1: Backend
cd backend
uv run uvicorn gtw.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev

# Opens at http://localhost:5173, connects to localhost:8000
```

---

## Build & Package

```bash
# Development
just dev          # Runs backend + frontend in parallel

# Build desktop app
just build        # Builds for current platform
just build-all    # Builds for macOS, Windows, Linux

# Plugin development
just plugin-new my-plugin    # Scaffold new plugin
just plugin-test my-plugin   # Run plugin tests
just plugin-pack my-plugin   # Package for distribution

# Release
just release 1.0.0           # Tag, build, sign, upload
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Tauri is newer than Electron | Tauri 2.0 is stable; fallback to Electron is straightforward |
| Python bundling is tricky | PyOxidizer is mature; PyInstaller as backup |
| WebSocket complexity | Simple protocol; extensive testing; reconnection logic |
| Plugin security | Plugins run in same process (trusted); future: sandboxing |
| Pixi.js learning curve | Good docs; team ramp-up time budgeted |
| Cross-platform Gambit | Bundle binaries per platform; fallback to Python-only solvers |

---

## Summary

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  FRONTEND          React 18 + TypeScript + Pixi.js + Zustand                  │
│  ─────────         Canvas rendering, UI components, state management           │
│                                                                                 │
│  COMMUNICATION     WebSocket (real-time) + REST (CRUD)                         │
│  ─────────────     JSON protocol, Pydantic-validated                           │
│                                                                                 │
│  BACKEND           Python 3.11 + FastAPI + Pydantic                            │
│  ───────           Game logic, analyses, plugins, LLM integration              │
│                                                                                 │
│  PLUGINS           Python packages + entry points                              │
│  ───────           Standard discovery, ABC interfaces, PyPI distribution       │
│                                                                                 │
│  ENGINES           pygambit + Gambit CLI + nashpy                              │
│  ───────           Subprocess calls, direct bindings                           │
│                                                                                 │
│  SHELL             Tauri 2.0 (Rust)                                            │
│  ─────             Desktop packaging, file system, auto-update                  │
│                                                                                 │
│  BUNDLING          PyOxidizer (Python) + Vite (frontend) + Tauri               │
│  ────────          Single installable per platform                             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Key decisions:**
1. Python for all logic—researcher extensibility wins
2. Web UI via Pixi.js—best canvas platform available
3. Tauri over Electron—smaller, faster, modern
4. Entry points for plugins—standard Python, no custom loader
5. WebSocket for live updates—natural for continuous analysis
