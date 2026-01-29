# Game Formats

This document describes the game file formats supported by the Game Theory Workbench.

## JSON Schema

A unified JSON Schema definition is available for validation of all game types:

| Schema File |
|-------------|
| [`schemas/game.schema.json`](schemas/game.schema.json) |

The schema uses a discriminated union pattern with `game_efg`, `game_nfg`, or `game_maid` to determine the game type.

Use this schema with any JSON Schema validator to validate your game files before uploading.

## Format Overview

| Format | Extension | Description |
|--------|-----------|-------------|
| JSON (Unified) | `.json` | Native format supporting EFG, NFG, and MAID games |
| Gambit EFG | `.efg` | Gambit's extensive form format |
| Gambit NFG | `.nfg` | Gambit's normal form format |
| Vegas DSL | `.vg` | Vegas domain-specific language |

---

## Unified JSON Format

All game types share common fields at the top level, with format-specific data in exactly one of `game_efg`, `game_nfg`, or `game_maid`.

### Common Fields

```json
{
  "id": "string",              // Unique identifier
  "title": "string",           // Display name
  "description": "string",     // Optional: longer description
  "players": ["string"],       // List of player/agent names
  "tags": ["string"],          // Optional: for categorization

  // Exactly ONE of the following:
  "game_efg": { ... },         // Extensive-form (tree) games
  "game_nfg": { ... },         // Normal-form (matrix) games
  "game_maid": { ... }         // Multi-Agent Influence Diagrams
}
```

---

## Extensive Form Games (`game_efg`)

Represents game trees with decision nodes and outcomes.

### Schema

```json
{
  "id": "trust-game",
  "title": "Trust Game",
  "description": "A sequential game where Alice decides whether to trust Bob.",
  "players": ["Alice", "Bob"],
  "tags": ["sequential", "2-player"],
  "game_efg": {
    "root": "node_id",           // ID of the root node
    "nodes": {
      "node_id": {
        "id": "string",
        "player": "string",           // Player who decides at this node
        "actions": [
          {
            "label": "string",        // Action name
            "target": "string",       // ID of next node or outcome
            "probability": 0.5,       // Optional: for behavior profiles
            "warning": "string"       // Optional: e.g., "Dominated by X"
          }
        ],
        "information_set": "string",  // Optional: for imperfect information
        "warning": "string"           // Optional: node-level warning
      }
    },
    "outcomes": {
      "outcome_id": {
        "label": "string",
        "payoffs": {
          "Player1": 1.0,
          "Player2": 2.0
        }
      }
    }
  }
}
```

### Example: Trust Game

```json
{
  "id": "trust-game",
  "title": "Trust Game",
  "description": "A sequential game where Alice decides whether to trust Bob, who can then honor or betray that trust.",
  "players": ["Alice", "Bob"],
  "tags": ["sequential", "2-player", "example"],
  "game_efg": {
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
    }
  }
}
```

### Information Sets

For games with imperfect information, nodes in the same information set share an `information_set` ID:

```json
{
  "game_efg": {
    "nodes": {
      "n_bob_after_high": {
        "id": "n_bob_after_high",
        "player": "Bob",
        "information_set": "bob_info_1",
        "actions": [...]
      },
      "n_bob_after_low": {
        "id": "n_bob_after_low",
        "player": "Bob",
        "information_set": "bob_info_1",
        "actions": [...]
      }
    }
  }
}
```

Nodes in the same information set must have identical available actions.

---

## Normal Form Games (`game_nfg`)

Represents strategic-form (matrix) games for 2 players.

### Schema

```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "players": ["Player1", "Player2"],  // Exactly 2 players
  "tags": ["string"],
  "game_nfg": {
    "strategies": [
      ["Row1", "Row2"],               // Player 1 strategies
      ["Col1", "Col2"]                // Player 2 strategies
    ],
    "payoffs": [
      [[1.0, 2.0], [3.0, 4.0]],      // Row 1: [P1,P2] for each column
      [[5.0, 6.0], [7.0, 8.0]]       // Row 2: [P1,P2] for each column
    ]
  }
}
```

### Example: Matching Pennies

```json
{
  "id": "matching-pennies",
  "title": "Matching Pennies",
  "description": "A zero-sum game where Matcher wins by matching coins and Mismatcher wins by differing.",
  "players": ["Matcher", "Mismatcher"],
  "tags": ["strategic-form", "2-player", "zero-sum"],
  "game_nfg": {
    "strategies": [["Heads", "Tails"], ["Heads", "Tails"]],
    "payoffs": [
      [[1.0, -1.0], [-1.0, 1.0]],
      [[-1.0, 1.0], [1.0, -1.0]]
    ]
  }
}
```

### Payoff Matrix Interpretation

For a game with strategies `[["A", "B"], ["X", "Y"]]`:

```
              Player 2
              X         Y
Player 1  A  [a1,a2]   [b1,b2]
          B  [c1,c2]   [d1,d2]

payoffs[0][0] = [a1, a2]  -- P1 plays A, P2 plays X
payoffs[0][1] = [b1, b2]  -- P1 plays A, P2 plays Y
payoffs[1][0] = [c1, c2]  -- P1 plays B, P2 plays X
payoffs[1][1] = [d1, d2]  -- P1 plays B, P2 plays Y
```

---

## MAID Format (`game_maid`)

Multi-Agent Influence Diagrams represent games as causal DAGs with decision, utility, and chance nodes.

### Schema

```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "players": ["Agent1", "Agent2"],    // Agents in the MAID
  "tags": ["string"],
  "game_maid": {
    "nodes": [
      {
        "id": "string",
        "type": "decision" | "utility" | "chance",
        "agent": "string",            // Required for decision/utility
        "domain": [...]               // Possible values
      }
    ],
    "edges": [
      {"source": "node_id", "target": "node_id"}
    ],
    "cpds": [
      {
        "node": "string",
        "parents": ["parent1", "parent2"],
        "values": [[...]]             // Probability/utility table
      }
    ]
  }
}
```

### Node Types

| Type | Description |
|------|-------------|
| `decision` | A choice made by an agent |
| `utility` | Payoff/reward for an agent |
| `chance` | Probabilistic event (nature) |

### Example: Prisoner's Dilemma as MAID

```json
{
  "id": "prisoners-dilemma-maid",
  "title": "Prisoner's Dilemma",
  "description": "The classic prisoner's dilemma modeled as a Multi-Agent Influence Diagram.",
  "players": ["Row", "Column"],
  "tags": ["maid", "2-player", "classic"],
  "game_maid": {
    "nodes": [
      {"id": "D1", "type": "decision", "agent": "Row", "domain": ["Cooperate", "Defect"]},
      {"id": "D2", "type": "decision", "agent": "Column", "domain": ["Cooperate", "Defect"]},
      {"id": "U1", "type": "utility", "agent": "Row", "domain": [-3, -2, -1, 0]},
      {"id": "U2", "type": "utility", "agent": "Column", "domain": [-3, -2, -1, 0]}
    ],
    "edges": [
      {"source": "D1", "target": "U1"},
      {"source": "D1", "target": "U2"},
      {"source": "D2", "target": "U1"},
      {"source": "D2", "target": "U2"}
    ],
    "cpds": [
      {
        "node": "U1",
        "parents": ["D1", "D2"],
        "values": [
          [1.0, 0.0, 0.0, 0.0],
          [0.0, 0.0, 0.0, 1.0],
          [0.0, 1.0, 0.0, 0.0],
          [0.0, 0.0, 1.0, 0.0]
        ]
      }
    ]
  }
}
```

---

## Gambit EFG Format

The Gambit extensive form format. See [Gambit documentation](https://gambitproject.readthedocs.io/en/latest/formats.html#the-extensive-game-efg-file-format) for full specification.

### Basic Structure

```
EFG 2 R "Game Title" { "Player1" "Player2" }

p "Root" 1 1 "Root Info Set" { "Action1" "Action2" } 0
p "Node2" 2 1 "P2 Info Set" { "A" "B" } 0
t "Outcome1" 1 "Terminal" { 1, 2 }
t "Outcome2" 2 "Terminal" { 0, 0 }
```

### Key Elements

- `EFG 2 R "Title" { players }` - Header with version, type, title, players
- `p` - Personal (decision) node
- `c` - Chance node with probabilities
- `t` - Terminal node with payoffs

### Example

```
EFG 2 R "Simple Game" { "Alice" "Bob" }

p "" 1 1 "" { "Left" "Right" } 0
p "" 2 1 "" { "Up" "Down" } 0
t "" 1 "" { 3, 1 }
t "" 2 "" { 0, 0 }
t "" 3 "" { 1, 3 }
```

---

## Gambit NFG Format

The Gambit normal form format. See [Gambit documentation](https://gambitproject.readthedocs.io/en/latest/formats.html#the-strategic-game-nfg-file-format) for full specification.

### Basic Structure

```
NFG 1 R "Game Title" { "Player1" "Player2" }
{ { "Strategy1" "Strategy2" } { "StrategyA" "StrategyB" } }
""
{ payoffs }
```

### Example

```
NFG 1 R "Prisoner's Dilemma" { "Row" "Column" }
{ { "Cooperate" "Defect" } { "Cooperate" "Defect" } }
""
{ -1 -1 -3 0 0 -3 -2 -2 }
```

The payoffs are listed in outcome order:
1. (Cooperate, Cooperate): Row=-1, Column=-1
2. (Cooperate, Defect): Row=-3, Column=0
3. (Defect, Cooperate): Row=0, Column=-3
4. (Defect, Defect): Row=-2, Column=-2

---

## Vegas DSL Format

[Vegas](https://github.com/elazarg/vegas/) is a domain-specific language for describing games. Vegas files compile to MAID format.

### Basic Structure

```
game main() {
  join PlayerName() $ initialStack;
  join PlayerName() $ initialStack;
  yield or split Player1(action1: type) Player2(action2: type);
  withdraw
    condition1 ? { Player1 -> payoff; Player2 -> payoff }
  : condition2 ? { Player1 -> payoff; Player2 -> payoff }
  :              { Player1 -> payoff; Player2 -> payoff }
}
```

### Key Elements

- `game main() { ... }` - Game definition block
- `join Player() $ N;` - Declare a player with initial stake N
- `yield P(x: T)` - Define a decision point with player actions
- `yield P1(x: T1) P2(y: T2)` - Define simultaneous decision point with player actions
- `withdraw` - Specify payoffs based on action combinations

### Example: Prisoner's Dilemma

```
// Prisoner's Dilemma in Vegas DSL
game main() {
  join A() $ 100;
  join B() $ 100;
  yield or split A(c: bool) B(c: bool);
  withdraw
    (A.c && B.c )   ? { A -> 100; B -> 100 }
  : (A.c && !B.c) ? { A -> 0; B -> 200 }
  : (!A.c && B.c) ? { A -> 200; B -> 0 }
  :                 { A -> 90; B -> 110 }
}
```

Vegas games are loaded as `VegasGame` and can be converted to MAID format for analysis.

---

## Format Conversion

The workbench supports conversion between formats where mathematically meaningful.

### Currently Supported Conversions

| From | To | Status | Notes |
|------|-----|--------|-------|
| Extensive | Normal | Implemented | 2-player games only |
| Normal | Extensive | Implemented | Creates sequential representation |
| MAID | Extensive | Implemented | Via PyCID plugin |
| MAID | Normal | Implemented | Chained: MAID → Extensive → Normal (2-player) |
| Vegas | MAID | Implemented | Via Vegas plugin |
| EFG | JSON Extensive | Implemented | Parsed via Gambit plugin |
| NFG | JSON Normal | Implemented | Parsed via Gambit plugin |
| VG | JSON Vegas | Implemented | Parsed via Vegas plugin |

### Using Conversions

Via API:
```bash
# Get extensive-form game as normal-form
curl http://localhost:8000/api/games/trust-game/as/normal
```

Conversions are cached for performance.

### Current Limitations

1. **2-player only**: Normal form conversion currently supports only 2-player games
2. **Size explosion**: Converting large extensive-form trees to normal form can produce very large matrices
3. **Information loss**: Converting extensive form with imperfect information to normal form loses timing/observability structure
4. **MAID complexity**: Complex MAIDs may produce large or deeply nested extensive-form trees

---

## Creating Game Files

### Tips

1. **Use unique IDs**: Each node, outcome, and game needs a unique identifier
2. **Validate player names**: Ensure payoff keys match player names exactly
3. **Check targets**: Every action target must point to a valid node or outcome
4. **Complete payoffs**: Every outcome must have payoffs for all players

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "Root node does not exist" | `root` ID not in `nodes` | Check root ID matches a node key |
| "Missing payoff for player" | Outcome payoffs incomplete | Add missing player to payoffs dict |
| "Action has no target" | Null or missing target | Set target to node or outcome ID |
| "Node unreachable from root" | Orphaned node | Ensure all nodes are connected |

### Validation

Upload your game to get instant validation feedback:

```bash
curl -X POST http://localhost:8000/api/games/upload \
  -F "file=@my-game.json"
```

The Validation plugin runs automatically and reports errors/warnings.
