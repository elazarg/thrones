# API Reference

Complete REST API documentation for the Game Theory Workbench.

**Base URL**: `http://localhost:8000/api`

> **Note on errors**: Error response shapes vary by endpoint. Most return `{"detail": "message"}`, but some include structured error objects. See examples in each section.

---

## Games API

### List Games

```
GET /api/games
```

Returns all loaded games.

**Response**: `200 OK`
```json
[
  {
    "id": "trust-game",
    "title": "Trust Game",
    "format": "extensive",
    "player_count": 2
  },
  {
    "id": "matching-pennies",
    "title": "Matching Pennies",
    "format": "normal",
    "player_count": 2
  }
]
```

---

### Get Game

```
GET /api/games/{game_id}
```

Returns a specific game by ID.

**Parameters**:
- `game_id` (path): The game identifier

**Response**: `200 OK`

For extensive-form games:
```json
{
  "id": "trust-game",
  "title": "Trust Game",
  "players": ["Alice", "Bob"],
  "root": "n_start",
  "nodes": {
    "n_start": {
      "id": "n_start",
      "player": "Alice",
      "actions": [
        {"label": "Trust", "target": "n_bob"},
        {"label": "Don't", "target": "o_decline"}
      ]
    },
    "n_bob": {
      "id": "n_bob",
      "player": "Bob",
      "actions": [
        {"label": "Honor", "target": "o_coop"},
        {"label": "Betray", "target": "o_betray"}
      ]
    }
  },
  "outcomes": {
    "o_coop": {"label": "Cooperate", "payoffs": {"Alice": 1, "Bob": 1}},
    "o_betray": {"label": "Betray", "payoffs": {"Alice": -1, "Bob": 2}},
    "o_decline": {"label": "Decline", "payoffs": {"Alice": 0, "Bob": 0}}
  },
  "version": "v1",
  "format_name": "extensive"
}
```

For normal-form games:
```json
{
  "id": "matching-pennies",
  "title": "Matching Pennies",
  "players": ["Matcher", "Mismatcher"],
  "strategies": [["Heads", "Tails"], ["Heads", "Tails"]],
  "payoffs": [
    [[1.0, -1.0], [-1.0, 1.0]],
    [[-1.0, 1.0], [1.0, -1.0]]
  ],
  "version": "v1",
  "format_name": "normal"
}
```

**Error**: `404 Not Found`
```json
{
  "detail": "Game not found: invalid-id"
}
```

---

### Get Game as Format

```
GET /api/games/{game_id}/as/{target_format}
```

Returns the game converted to a specific format. Conversions are cached.

**Parameters**:
- `game_id` (path): The game identifier
- `target_format` (path): Target format - `"extensive"` or `"normal"`

**Response**: `200 OK` - Game in the requested format

**Errors**:
- `400 Bad Request`: Invalid format or conversion not possible
- `404 Not Found`: Game not found

**Example**:
```bash
# Get an extensive-form game as normal-form
curl http://localhost:8000/api/games/trust-game/as/normal
```

---

### Upload Game

```
POST /api/games/upload
```

Upload and parse a game file.

**Content-Type**: `multipart/form-data`

**Parameters**:
- `file` (form): The game file (`.efg`, `.nfg`, or `.json`)

**Response**: `200 OK` - The parsed game

**Errors**:
- `400 Bad Request`: Invalid file or parse error (includes error message for debugging)
  ```json
  {
    "detail": "Invalid game format: my-game.json - Root node 'n_start' does not exist"
  }
  ```

**Example**:
```bash
curl -X POST http://localhost:8000/api/games/upload \
  -F "file=@trust-game.json"
```

---

### Delete Game

```
DELETE /api/games/{game_id}
```

Remove a game from the store.

**Parameters**:
- `game_id` (path): The game identifier

**Response**: `200 OK`
```json
{
  "status": "deleted",
  "id": "trust-game"
}
```

**Error**: `404 Not Found`

---

## Analyses API

### List Available Analyses

```
GET /api/analyses
```

Returns information about all registered analysis plugins.

**Response**: `200 OK`
```json
[
  {
    "name": "Validation",
    "description": "Checks game structure for errors and warnings",
    "applicable_to": ["extensive", "strategic"],
    "continuous": true
  },
  {
    "name": "Nash Equilibrium",
    "description": "Computes Nash equilibria using Gambit solvers",
    "applicable_to": ["extensive", "normal"],
    "continuous": true
  }
]
```

---

### Run Continuous Analyses

```
GET /api/games/{game_id}/analyses
```

Runs all `continuous` analysis plugins on the specified game and returns results synchronously. Attempts format conversion if a plugin cannot run on the native game format.

**Parameters**:
- `game_id` (path): The game identifier
- `solver` (query, optional): Nash solver type - `"exhaustive"` (default), `"quick"`, or `"pure"`
- `max_equilibria` (query, optional): Maximum equilibria to find (for `"quick"` solver)

**Response**: `200 OK`

Each result includes `plugin_name` for attribution and `computation_time_ms` in details:

```json
[
  {
    "plugin_name": "Validation",
    "result": {
      "summary": "Valid",
      "details": {
        "errors": [],
        "warnings": [],
        "computation_time_ms": 2
      }
    }
  },
  {
    "plugin_name": "Nash Equilibrium",
    "result": {
      "summary": "2 equilibria found",
      "details": {
        "equilibria": [...],
        "computation_time_ms": 45
      }
    }
  }
]
```

**Conversion Fallback**: If a plugin cannot run on the game's native format, the backend automatically attempts to convert the game to formats listed in the plugin's `applicable_to` list.

**Error**: `404 Not Found` if game doesn't exist

**Note**: This endpoint is for quick, synchronous analyses. For long-running computations, use the Tasks API below.

---

## Tasks API

Tasks provide asynchronous execution for long-running analyses. Task submission uses **query parameters** (not a JSON body).

### Submit Task

```
POST /api/tasks
```

Submit an analysis task for async execution. Parameters are passed as **query parameters**.

**Query Parameters**:
- `game_id` (required): ID of the game to analyze
- `plugin` (required): Name of the analysis plugin
- `owner` (optional): Client identifier (default: `"anonymous"`)
- `solver` (optional): Solver variant for Nash equilibrium
- `max_equilibria` (optional): Maximum number of equilibria to compute

**Response**: `200 OK`

Returns the full task object (same structure as `GET /api/tasks/{id}`):

```json
{
  "id": "abc123",
  "owner": "anonymous",
  "status": "pending",
  "plugin_name": "Nash Equilibrium",
  "game_id": "trust-game",
  "config": {},
  "result": null,
  "error": null,
  "created_at": 1706500000.0,
  "started_at": null,
  "completed_at": null
}
```

**Conversion Fallback**: If the plugin cannot run on the game's native format, the backend automatically attempts to convert the game to formats listed in the plugin's `applicable_to` list. The first successful conversion is used. For example, a Nash plugin may convert a MAID game to extensive form before analysis.

**Errors**:
- `400 Bad Request`: Plugin unavailable, incompatible with game format (even after conversion attempts), or unknown plugin
  ```json
  {"detail": "Unknown plugin: BadPlugin. Available: ['Nash Equilibrium', 'IESDS', 'Validation']"}
  ```
  ```json
  {"detail": "Plugin 'Nash Equilibrium' cannot run on this game (format: maid)"}
  ```
- `404 Not Found`: Game not found
  ```json
  {"detail": "Game not found: invalid-id"}
  ```

**Example**:
```bash
curl -X POST "http://localhost:8000/api/tasks?game_id=trust-game&plugin=Nash%20Equilibrium"
```

---

### Get Task

```
GET /api/tasks/{task_id}
```

Get task status and result.

**Parameters**:
- `task_id` (path): The task identifier

**Response**: `200 OK`

> **Note**: Task objects use `id` field (not `task_id`). The full object structure is returned.

Pending task:
```json
{
  "id": "abc123",
  "owner": "anonymous",
  "status": "pending",
  "plugin_name": "Nash Equilibrium",
  "game_id": "trust-game",
  "config": {},
  "result": null,
  "error": null,
  "created_at": 1706500000.0,
  "started_at": null,
  "completed_at": null
}
```

Completed task:
```json
{
  "id": "abc123",
  "owner": "anonymous",
  "status": "completed",
  "plugin_name": "Nash Equilibrium",
  "game_id": "trust-game",
  "config": {"solver": "exhaustive"},
  "result": {
    "summary": "2 equilibria found",
    "details": {
      "equilibria": [...],
      "computation_time_ms": 45
    }
  },
  "error": null,
  "created_at": 1706500000.0,
  "started_at": 1706500000.5,
  "completed_at": 1706500001.2
}
```

Failed task:
```json
{
  "id": "abc123",
  "owner": "anonymous",
  "status": "failed",
  "plugin_name": "Nash Equilibrium",
  "game_id": "trust-game",
  "config": {},
  "result": null,
  "error": "TimeoutError: computation exceeded limit",
  "created_at": 1706500000.0,
  "started_at": 1706500000.5,
  "completed_at": 1706500060.0
}
```

**Error**: `404 Not Found`
```json
{"detail": "Task not found: invalid-id"}
```

---

### Cancel Task

```
DELETE /api/tasks/{task_id}
```

Request cancellation of a running task. Returns the current task state.

**Parameters**:
- `task_id` (path): The task identifier

**Response**: `200 OK`

Successful cancellation (task was pending or running):
```json
{
  "cancelled": true,
  "task": {
    "id": "abc123",
    "owner": "anonymous",
    "status": "running",
    "plugin_name": "Nash Equilibrium",
    "game_id": "trust-game",
    "config": {},
    "result": null,
    "error": null,
    "created_at": 1706500000.0,
    "started_at": 1706500000.5,
    "completed_at": null
  }
}
```

If task already finished:
```json
{
  "cancelled": false,
  "reason": "Task already completed",
  "task": {
    "id": "abc123",
    "status": "completed",
    ...
  }
}
```

**Error**: `404 Not Found`

---

### List Tasks

```
GET /api/tasks
```

List all tasks, optionally filtered by owner.

**Query Parameters**:
- `owner` (optional): Filter by owner identifier

**Response**: `200 OK`
```json
[
  {
    "id": "abc123",
    "status": "completed",
    "owner": "session-xyz",
    "game_id": "trust-game",
    "plugin_name": "Nash Equilibrium"
  },
  {
    "id": "def456",
    "status": "running",
    "owner": "session-xyz",
    "game_id": "prisoners-dilemma",
    "plugin_name": "IESDS"
  }
]
```

---

## Plugins API

### Check Analysis Applicability

```
GET /api/plugins/check-applicable/{game_id}
```

Check which analyses are applicable to a specific game. Queries each plugin's `/check-applicable` endpoint and aggregates results. Plugins that don't implement this endpoint are assumed to be always applicable.

**Parameters**:
- `game_id` (path): The game identifier

**Response**: `200 OK`
```json
{
  "game_id": "rock-paper-scissors",
  "analyses": {
    "Replicator Dynamics": {
      "applicable": true
    },
    "Evolutionary Stability": {
      "applicable": false,
      "reason": "Requires symmetric game (got 3x2)"
    }
  }
}
```

If game not found:
```json
{
  "error": "Game not found: invalid-id"
}
```

---

## Utility API

### Health Check

```
GET /api/health
```

Check if the server is running.

**Response**: `200 OK`
```json
{
  "status": "ok",
  "games_loaded": 6
}
```

---

### Reset State

```
POST /api/reset
```

Clear all loaded games and reload example games.

**Response**: `200 OK`
```json
{
  "status": "reset",
  "games_cleared": 8
}
```

---

## Schemas

### ExtensiveFormGame

```typescript
interface ExtensiveFormGame {
  id: string;
  title: string;
  players: string[];
  root: string;                    // ID of root node
  nodes: Record<string, DecisionNode>;
  outcomes: Record<string, Outcome>;
  version: string;
  tags: string[];
  format_name: "extensive";
}

interface DecisionNode {
  id: string;
  player: string;
  actions: Action[];
  information_set?: string;        // For imperfect information
  warning?: string;
}

interface Action {
  label: string;
  target: string;                  // Node or outcome ID
  probability?: number;            // For behavior profiles
  warning?: string;
}

interface Outcome {
  label: string;
  payoffs: Record<string, number>; // player -> payoff
}
```

### NormalFormGame

```typescript
interface NormalFormGame {
  id: string;
  title: string;
  players: [string, string];       // Exactly 2 players
  strategies: [string[], string[]]; // Strategies per player
  payoffs: [number, number][][];   // [row][col] -> [P1, P2] payoffs
  version: string;
  tags: string[];
  format_name: "normal";
}
```

### MAIDGame

```typescript
interface MAIDGame {
  id: string;
  title: string;
  agents: string[];
  nodes: MAIDNode[];
  edges: MAIDEdge[];
  cpds: TabularCPD[];
  version: string;
  tags: string[];
  format_name: "maid";
}

interface MAIDNode {
  id: string;
  type: "chance" | "decision" | "utility";
  agent?: string;                  // Required for decision/utility
  domain: any[];
}

interface MAIDEdge {
  source: string;
  target: string;
}

interface TabularCPD {
  node: string;
  parents: string[];
  values: number[][];
}
```

### AnalysisResult

```typescript
interface AnalysisResult {
  summary: string;
  details: Record<string, any>;
}
```

### PluginAnalysisResult

Used by `GET /api/games/{id}/analyses` to include plugin attribution:

```typescript
interface PluginAnalysisResult {
  plugin_name: string;
  result: AnalysisResult;
}
```

### AnalysisInfo

Used by `GET /api/analyses` to describe available plugins:

```typescript
interface AnalysisInfo {
  name: string;
  description: string;
  applicable_to: string[];  // e.g., ["extensive", "normal"]
  continuous: boolean;
}
```

### Task

```typescript
interface Task {
  id: string;
  owner: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  plugin_name: string;
  game_id: string;
  config: Record<string, any>;
  result: AnalysisResult | null;
  error: string | null;
  created_at: number;              // Unix timestamp (seconds)
  started_at: number | null;
  completed_at: number | null;
}
```

### Error Responses

Error shapes vary by endpoint. Common patterns:

```typescript
// Most endpoints (FastAPI default)
{ "detail": "Human-readable error message" }

// Plugin errors (remote plugins)
{
  "detail": {
    "error": {
      "code": "PARSE_ERROR",
      "message": "Failed to parse EFG: unexpected token"
    }
  }
}

// Validation errors (Pydantic)
{
  "detail": [
    {
      "loc": ["query", "game_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Examples

### cURL

```bash
# List games
curl http://localhost:8000/api/games

# Get a specific game
curl http://localhost:8000/api/games/trust-game

# Upload a game file
curl -X POST http://localhost:8000/api/games/upload \
  -F "file=@my-game.json"

# Run Nash equilibrium analysis
curl -X POST "http://localhost:8000/api/tasks?game_id=trust-game&plugin=Nash%20Equilibrium"

# Check task status
curl http://localhost:8000/api/tasks/abc123

# Cancel a task
curl -X DELETE http://localhost:8000/api/tasks/abc123
```

### Python (requests)

```python
import requests
import time

BASE_URL = "http://localhost:8000/api"

# List games
games = requests.get(f"{BASE_URL}/games").json()
print(f"Loaded games: {[g['id'] for g in games]}")

# Get a game
game = requests.get(f"{BASE_URL}/games/trust-game").json()
print(f"Game: {game['title']} with players {game['players']}")

# List available analyses
analyses = requests.get(f"{BASE_URL}/analyses").json()
print(f"Available: {[a['name'] for a in analyses]}")

# Upload a file
with open("my-game.json", "rb") as f:
    response = requests.post(f"{BASE_URL}/games/upload", files={"file": f})
    uploaded = response.json()
    print(f"Uploaded: {uploaded['id']}")

# Run analysis (returns full task object)
response = requests.post(
    f"{BASE_URL}/tasks",
    params={"game_id": "trust-game", "plugin": "Nash Equilibrium"}
)
task = response.json()
task_id = task["id"]  # Note: uses 'id', not 'task_id'

# Poll for completion
while task["status"] not in ("completed", "failed", "cancelled"):
    task = requests.get(f"{BASE_URL}/tasks/{task_id}").json()
    time.sleep(0.5)

if task["status"] == "completed":
    print(f"Result: {task['result']['summary']}")
else:
    print(f"Task {task['status']}: {task.get('error', 'unknown error')}")
```

### JavaScript (fetch)

```javascript
const BASE_URL = 'http://localhost:8000/api';

// List games
const games = await fetch(`${BASE_URL}/games`).then(r => r.json());
console.log('Games:', games.map(g => g.id));

// Get a game
const game = await fetch(`${BASE_URL}/games/trust-game`).then(r => r.json());
console.log(`Game: ${game.title}`);

// List available analyses
const analyses = await fetch(`${BASE_URL}/analyses`).then(r => r.json());
console.log('Available:', analyses.map(a => a.name));

// Upload a file
const formData = new FormData();
formData.append('file', fileInput.files[0]);
const uploaded = await fetch(`${BASE_URL}/games/upload`, {
  method: 'POST',
  body: formData
}).then(r => r.json());

// Run analysis (returns full task object with 'id')
const task = await fetch(
  `${BASE_URL}/tasks?game_id=trust-game&plugin=Nash%20Equilibrium`,
  { method: 'POST' }
).then(r => r.json());

const pollTask = async (taskId) => {
  while (true) {
    const task = await fetch(`${BASE_URL}/tasks/${taskId}`).then(r => r.json());
    if (['completed', 'failed', 'cancelled'].includes(task.status)) {
      return task;
    }
    await new Promise(r => setTimeout(r, 500));
  }
};

const result = await pollTask(task.id);  // Note: uses 'id', not 'task_id'
console.log('Analysis:', result.result?.summary);
```
