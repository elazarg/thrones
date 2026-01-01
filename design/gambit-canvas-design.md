# Game Theory Workbench: A Canvas-Centric Design

## Philosophy

This is a **game theory workbench** that happens to use Gambit (among other engines) for computation. The core is a canvas where games live, analyses run continuously, and results appear as visual annotations rather than separate panels.

### Core Principles

1. **The canvas is primary.** Games are drawn, manipulated, and understood visually. Analyses decorate the canvas; they don't live in separate windows.

2. **Continuous, not modal.** Validation runs as you edit. Equilibrium computation runs when you pause. Results update live. No "validate" button, no "analyze" mode.

3. **LLM as collaborator, not wizard.** Natural language input is always available—for creating, modifying, querying. "Make this simultaneous" or "What if payoffs were symmetric?" works anytime.

4. **Everything is a plugin.** Formats (EFG, NFG, MAID, CGT), analyses (Nash, SPE, QRE, dominance), visualizations (tree, matrix, DAG), and simulations are all plugins. The core is just: canvas + history + plugin registry.

5. **Mistakes are cheap.** Continuous versioning means any state is recoverable. LLM hallucinations, bad edits, failed experiments—all reversible.

6. **Simulations are first-class.** Playing out games—with policies, AI agents, or humans—is as natural as solving them.

---

## The Canvas

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Trust Game                [+v3]     [Plugins ▾]  [Simulate ▶]  [💬 LLM]       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│                            ○ Alice                                              │
│                          ╱    ╲                                                 │
│                   Trust ╱      ╲ Don't                                          │
│                 ┃┃┃┃┃┃ ╱        ╲ ┃                 ← thickness = P(play)       │
│                       ╱          ╲                                              │
│               ┌─────○ Bob─────────□ (0,0)                                      │
│               │    ╱    ╲           ↑                                           │
│        NE₁───▶│   ╱      ╲          never reached                              │
│               │  ╱        ╲                                                     │
│               ▼ □          □                                                    │
│             ★(1,1)      (-1,2)      ★ = equilibrium outcome                    │
│                            ↑                                                    │
│                     ⚠ dominated by Honor                                       │
│                                                                                 │
│  ╭──────────────────────────────────────────────────────────────────────────╮  │
│  │ 💬  what if bob moves first?                                             │  │
│  ╰──────────────────────────────────────────────────────────────────────────╯  │
│                                                                                 │
├────────────────────────────────┬────────────────────────────────────────────────┤
│ ✓ Valid │ 2 NE │ Dom: Betray  │ Hover for details • Click to expand • ⚙ Config │
└────────────────────────────────┴────────────────────────────────────────────────┘
```

### Visual Language

Everything that can be shown on the canvas, is:

| Analysis Result | Visual Representation |
|-----------------|----------------------|
| Equilibrium play probability | Branch thickness |
| Dominated strategy | Faded/ghosted + ⚠ icon |
| Validation error | Red border + tooltip |
| Validation warning | Yellow border + tooltip |
| Information set | Dashed enclosure, shared color |
| Unreachable node | Dotted lines, grayed out |
| Selected equilibrium | ★ at terminal, highlighted path |
| Simulation trace | Animated traversal |
| Belief (Bayesian) | Probability badge at info set |

### The Status Bar

The bottom bar shows **live results** from running analyses:

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ ✓ Valid │ 2 Nash eq │ 1 SPE │ Dom: P2.Betray │ QRE: λ=2.3 │ ⏱ 12ms │ ⚙       │
└────────────────────────────────────────────────────────────────────────────────┘
```

- **Click any item** → Expands to show details
- **Hover** → Quick preview tooltip
- **⚙** → Configure which analyses run, thresholds, display options

When an analysis is computing:
```
│ ✓ Valid │ 2 Nash eq │ ◐ SPE... │ Dom: P2.Betray │
```

When an analysis fails or times out:
```
│ ✓ Valid │ ⚠ Nash: >100 eq, showing 10 │ ✗ SPE: timeout │
```

---

## Continuous LLM Integration

The LLM prompt is always visible (collapsible). It's not for "creating from scratch"—it's for **continuous transformation**.

### Creation
```
💬 a prisoner's dilemma with a third "negotiate" option that costs 1 but reveals intentions
```

### Modification
```
💬 make this zero-sum
💬 add a signaling stage before Alice moves  
💬 what if Player 2 could commit to a strategy?
💬 duplicate this game but swap the players
```

### Queries
```
💬 why is Betray dominated?
💬 explain the mixed equilibrium
💬 what would change if payoff (1,1) became (2,1)?
```

### How It Works

1. LLM generates a **proposed new game state** (or explanation)
2. Proposal shown as a **diff preview** on canvas (additions green, removals red)
3. User accepts, rejects, or refines
4. Accepted changes create a **new version** automatically
5. All analyses re-run on new version

Because versioning is automatic, LLM mistakes are low-cost. User can always revert, branch, or compare.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  💬 LLM Proposal: "Add signaling stage"                    [Accept] [Reject]   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│                     ┌─────────────────────┐                                     │
│                     │  + ○ Alice          │  ← NEW                              │
│                     │  Signal / No Signal │                                     │
│                     └──────────┬──────────┘                                     │
│                                │                                                │
│                            ○ Alice                                              │
│                          ╱    ╲                                                 │
│                   Trust ╱      ╲ Don't                                          │
│                       ...                                                       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Plugin Architecture

The workbench is a thin core with thick plugins.

### Core (Non-Negotiable)

- Canvas rendering engine
- Version/history system  
- Plugin registry and lifecycle
- LLM integration layer
- Persistence (local files, export)

### Everything Else Is A Plugin

```
plugins/
├── formats/
│   ├── efg/              # Gambit extensive form
│   ├── nfg/              # Gambit normal form
│   ├── maid/             # Multi-agent influence diagrams
│   ├── cgt/              # Combinatorial game theory
│   ├── json/             # Generic JSON serialization
│   └── ...
├── analyses/
│   ├── validation/       # Structure checks
│   ├── nash/             # Nash equilibrium (wraps gambit-*)
│   ├── spe/              # Subgame perfect
│   ├── qre/              # Quantal response
│   ├── dominance/        # Iterated dominance
│   ├── correlated/       # Correlated equilibrium
│   └── ...
├── visualizations/
│   ├── tree/             # Extensive form tree
│   ├── matrix/           # Normal form table
│   ├── dag/              # For MAIDs and similar
│   ├── payoff-space/     # 2D/3D payoff plots
│   └── ...
├── simulations/
│   ├── random/           # Random play
│   ├── best-response/    # Best-response dynamics
│   ├── fictitious-play/  # Fictitious play
│   ├── llm-agents/       # LLM-based players
│   ├── mcts/             # Monte Carlo tree search
│   ├── human/            # Human-in-the-loop
│   └── ...
└── engines/
    ├── gambit/           # Gambit CLI tools
    ├── nashpy/           # Python Nash solvers
    ├── lemke-howson/     # Direct implementation
    └── ...
```

### Plugin Interface (Sketch)

```python
class AnalysisPlugin:
    """Base class for analysis plugins."""
    
    # Metadata
    name: str
    description: str
    applicable_to: list[str]  # ["extensive", "normal", "maid", ...]
    
    # Behavior
    continuous: bool          # Run automatically as game changes?
    timeout_default: float    # Seconds before giving up
    
    def can_run(self, game: Game) -> bool:
        """Check if analysis applies to this game."""
        
    def run(self, game: Game, config: dict) -> AnalysisResult:
        """Execute the analysis."""
        
    def render(self, result: AnalysisResult, canvas: Canvas) -> None:
        """Draw results on canvas (optional, for overlays)."""
        
    def summarize(self, result: AnalysisResult) -> str:
        """One-line summary for status bar."""
```

### Example: Nash Equilibrium Plugin

```python
class NashEquilibriumPlugin(AnalysisPlugin):
    name = "Nash Equilibrium"
    applicable_to = ["extensive", "normal"]
    continuous = True
    timeout_default = 5.0
    
    def run(self, game, config):
        # Choose engine based on game size and config
        if game.is_two_player and game.strategy_count < 100:
            return self.engines.gambit.enummixed(game)
        else:
            return self.engines.gambit.gnm(game, **config)
    
    def render(self, result, canvas):
        for eq in result.equilibria:
            # Thickness encodes probability
            for action, prob in eq.behavior_profile.items():
                canvas.set_edge_thickness(action.edge, prob)
            # Star marks equilibrium outcomes
            for terminal, prob in eq.outcome_distribution.items():
                if prob > 0.01:
                    canvas.add_marker(terminal, "★", opacity=prob)
    
    def summarize(self, result):
        n = len(result.equilibria)
        if n == 0:
            return "No Nash eq"
        elif n == 1:
            return "1 Nash eq"
        else:
            return f"{n} Nash eq"
```

---

## Simulations

Simulations are how games come alive. They're not secondary to equilibrium analysis—they're complementary.

### Simulation Types

**Algorithmic agents**: Best response, fictitious play, regret matching, MCTS, CFR

**AI agents**: LLM-based players with configurable prompts/personas

**Human players**: Local hot-seat or networked play

**Hybrid**: Mix of the above (e.g., human vs. LLM, or human with AI suggestions)

### Simulation Interface

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🎮 SIMULATION                                              [Run] [Step] [Stop] │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Players:                                                                       │
│    Alice: [LLM Agent ▾]  "Play cautiously, value cooperation"                  │
│    Bob:   [Best Response ▾]                                                    │
│                                                                                 │
│  Repetitions: [100]    Speed: [Fast ▾]    Show: ☑ Trace  ☑ Statistics         │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Run 47/100:  Alice → Trust → Bob → Honor → (1,1)                             │
│                                                                                 │
│  Aggregate (47 runs):                                                          │
│    Trust,Honor: 34 (72%)    Trust,Betray: 8 (17%)                              │
│    Don't,─:     5 (11%)                                                        │
│                                                                                 │
│  Mean payoffs: Alice=0.83, Bob=0.94                                            │
│                                                                                 │
│  vs. Nash prediction: Alice=0.67, Bob=1.17  [Compare ▾]                        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Simulation on Canvas

During simulation, the canvas animates:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│                            ◉ Alice          ← pulsing: current decision        │
│                          ╱    ╲                                                 │
│                  →Trust ╱      ╲ Don't                                          │
│                 ══════ ╱        ╲            ══ = chosen path                   │
│                       ╱          ╲                                              │
│                      ○ Bob────────□ (0,0)                                       │
│                    ╱    ╲                                                       │
│              Honor╱      ╲Betray                                                │
│                  ╱        ╲                                                     │
│                 □          □                                                    │
│             ★(1,1)      (-1,2)              ★ = destination this run           │
│                                                                                 │
│  ┌─────────────────────────────────────────┐                                   │
│  │ 🤖 Alice (LLM): "I'll trust—Bob has    │   ← agent reasoning (if available)│
│  │    honored before, and cooperation      │                                   │
│  │    builds value long-term."             │                                   │
│  └─────────────────────────────────────────┘                                   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Agent Configuration

```yaml
# Example LLM agent config
type: llm
model: claude-sonnet
system_prompt: |
  You are playing a game as {player_name}.
  Your personality: {persona}
  You see: {game_description}
  History so far: {history}
  Your available actions: {actions}
  Choose an action and explain briefly.
persona: "A cautious player who values long-term cooperation over short-term gains"
temperature: 0.7
```

---

## Versioning

Every meaningful change creates a version. Not "save points"—continuous history.

### The Version Model

```
Trust Game
├── v1: Initial creation (LLM: "prisoner's dilemma")
├── v2: Added third option (LLM: "add negotiate option")
├── v3: Changed payoff (3,3) → (2,2) (manual edit)
├── v4: Made simultaneous (LLM: "make this simultaneous")
│   └── v4.1: Branch—tried zero-sum variant
└── v5: Current (manual edit: renamed strategies)
```

### Version UI

Minimal—don't interrupt flow:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Trust Game                [v5 ▾]                                              │
│                            ├── v5: Current                                      │
│                            ├── v4.1: (branch) zero-sum variant                 │
│                            ├── v4: Made simultaneous                            │
│                            ├── v3: Changed payoff                               │
│                            ├── v2: Added negotiate                              │
│                            └── v1: Initial                                      │
│                            ─────────────                                        │
│                            [Compare...] [Branch from here]                     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Comparison View

Select two versions → see diff on canvas:

```
v3 → v4: "Made simultaneous"

  v3 (sequential):              v4 (simultaneous):
       ○ Alice                    ┌─────────────┐
      ╱    ╲                      │ Alice × Bob │
   T ╱      ╲ D                   ├─────┬───────┤
    ○ Bob    □                    │     │ H   B │
   ╱  ╲                           │ T   │ 1,1 │-1,2│
  □    □                          │ D   │ 0,0 │ 0,0│
                                  └─────┴───────┘
```

---

## Configuration

Analyses run continuously with sensible defaults, but users control the details.

### Analysis Configuration Panel

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ⚙ Running Analyses                                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ☑ Validation              Always     ─────────────────────                    │
│  ☑ Nash Equilibrium        Auto       Timeout: [5s]  Max: [20] eq              │
│  ☑ Dominance               Auto       ☑ Strict  ☑ Weak  ☐ Mixed                │
│  ☐ Subgame Perfect         Manual     [Run Now]                                │
│  ☐ QRE                     Manual     λ range: [0.1 to 10]                     │
│  ☐ Correlated Eq           Manual     [Run Now]                                │
│                                                                                 │
│  [+ Add Analysis Plugin...]                                                    │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Display:                                                                       │
│    ☑ Show probabilities on branches                                            │
│    ☑ Fade dominated strategies                                                 │
│    ☑ Mark equilibrium outcomes                                                 │
│    ☐ Show belief annotations                                                   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Auto** = Runs when game changes and stabilizes (debounced)
**Always** = Runs on every edit
**Manual** = Only on explicit request

---

## Multi-Agent Influence Diagrams (MAIDs)

Since you mentioned MAIDs specifically—they're a natural fit for the canvas model but require a different visualization plugin.

### MAID View (DAG instead of Tree)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Insurance MAID               [View: DAG ▾]                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│         ◇ Weather              ◇ = chance node                                 │
│           │                    □ = decision node                               │
│           ▼                    ◆ = utility node                                │
│    ┌──────┴──────┐                                                             │
│    ▼             ▼                                                             │
│  □ Insurer    □ Farmer         Edges show information flow                     │
│  (offer)      (accept?)                                                        │
│    │             │                                                             │
│    ▼             ▼                                                             │
│  ◆ Insurer    ◆ Farmer                                                        │
│    Utility      Utility                                                        │
│                                                                                 │
│  ─────────────────────────────                                                 │
│  Selected: Farmer.accept                                                       │
│  Parents: Weather, Insurer.offer                                               │
│  Domain: {accept, reject}                                                      │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ✓ Valid MAID │ Computing NE... │ 2 strategic relevance links │                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### MAID-Specific Analyses (Plugins)

- **Strategic relevance**: Which decisions affect which utilities?
- **S-reachability**: Information flow analysis
- **MAID Nash**: Equilibrium in the induced game
- **Value of information**: What if a node observed another?

These are just plugins—same architecture, different visualizations and computations.

---

## Detailed Popups (On Demand)

The status bar shows summaries. Clicking expands without leaving the canvas:

### Equilibrium Detail Popup

```
                    ┌─────────────────────────────────────────┐
                    │ Nash Equilibrium #1 (Pure)              │
                    ├─────────────────────────────────────────┤
                    │                                         │
                    │ Strategies:                             │
                    │   Alice: Trust (100%)                   │
                    │   Bob: Honor (100%)                     │
                    │                                         │
                    │ Payoffs: (1, 1)                         │
                    │                                         │
│ ✓ Valid │ [2 NE] │ │ Properties:                            │
          ▲        │   ✓ Pareto efficient                    │
          │        │   ✓ Subgame perfect                     │
          │        │   ✓ Payoff dominant                     │
          │        │                                         │
          │        │ Computed by: gambit-enummixed           │
          │        │ Time: 3ms                               │
          │        │                                         │
          │        │ [Show on Canvas] [Compare] [Export]     │
          │        └─────────────────────────────────────────┘
          │
     click here
```

### Validation Warning Popup

```
  ┌─────────────────────────────────────────────┐
  │ ⚠ Dominated Strategy                        │
  ├─────────────────────────────────────────────┤
  │                                             │
  │ Player 2's "Betray" is strictly dominated   │
  │ by "Honor" in the subgame after Trust.      │
  │                                             │
  │ Implication: Rational P2 never plays Betray │
  │ after Trust, though it may still be played  │
  │ off-equilibrium-path.                       │
  │                                             │
  │ [Show Dominance Proof] [Eliminate Strategy] │
  │                                             │
  └─────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│ ✓ Valid │ 2 NE │ [Dom: P2.Betray] │                     │
```

---

## Interaction Summary

| Want to... | Do this |
|------------|---------|
| Create a game | Type in LLM box, or start drawing on canvas |
| Edit structure | Drag nodes, click to add/remove, direct manipulation |
| Edit payoffs | Click payoff → type → tab to next |
| See equilibria | Look at canvas (thickness, stars) or click status bar |
| Understand result | Hover for tooltip, click for detail popup |
| Run specific analysis | Click ⚙, enable it, or right-click → "Run X" |
| Modify via LLM | Type transformation in LLM box |
| Undo/redo | Ctrl+Z / Ctrl+Y (or click version dropdown) |
| Compare versions | Version dropdown → Compare |
| Simulate | Click Simulate → configure agents → Run |
| Export | Right-click → Export, or File menu |
| Add plugin | Settings → Plugins → Browse/Install |

---

## What This Is Not

**Not a form-based workflow.** No "Step 1: Create, Step 2: Validate, Step 3: Analyze." Everything is fluid.

**Not Gambit-specific.** Gambit is one engine among potentially many. The workbench outlives any single solver.

**Not complete.** This design describes what's *supportable*, not what's implemented day one. Plugin architecture means capabilities grow without core changes.

**Not prescriptive about technology.** Could be web (Canvas/WebGL), desktop (Qt/GTK), or hybrid. The design is interaction patterns, not implementation.

---

## Implementation Priorities

If building incrementally:

### Phase 1: Canvas Core
- Basic tree rendering and editing
- Direct manipulation (drag, click-to-edit)
- EFG import/export
- Single equilibrium solver (gambit-enummixed)
- Status bar with live results
- Version history (linear)

### Phase 2: Continuous Analysis
- Plugin architecture for analyses
- Multiple simultaneous analyses
- Visual overlays (thickness, fading, markers)
- Configuration panel
- Detail popups

### Phase 3: LLM Integration
- Prompt input
- Diff preview
- Accept/reject flow
- Versioning integration

### Phase 4: Simulations
- Algorithmic agents
- Simulation runner
- Aggregate statistics
- Canvas animation

### Phase 5: Ecosystem
- Plugin marketplace/registry
- Additional formats (NFG, MAID, ...)
- Additional engines
- LLM agents
- Collaborative editing

---

## Success Criteria

The workbench succeeds if:

1. **Flow is uninterrupted.** User thinks about the game, not the tool. No mode switches, no waiting for dialogs.

2. **Results are glanceable.** Canvas tells the story. Details available on demand but not required.

3. **Experimentation is cheap.** "What if..." costs a sentence typed and seconds waited. Wrong turns cost nothing (revert).

4. **Analyses are trustworthy.** Provenance is clear. Numerical issues are visible. Multiple solvers can cross-check.

5. **Growth is organic.** New formats, solvers, visualizations arrive as plugins without disrupting existing work.

The measure isn't feature count—it's whether a researcher can load a game, understand its equilibria, try three variations, and export results in under five minutes without reading documentation.
