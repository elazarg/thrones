# Game Theory Workbench

Analyze, visualize, and explore strategic games. Compute Nash equilibria, check dominance, run evolutionary simulations, and more—all through an interactive web interface.

## What You Can Do

### Equilibrium Analysis
- **Nash Equilibria**: Find pure and mixed-strategy Nash equilibria for any game
- **Subgame Perfect Equilibria**: Compute SPE for extensive-form and MAID games
- **Dominance Analysis**: Identify dominated strategies via IESDS (iterated elimination)
- **Exploitability**: Measure how far a strategy is from equilibrium play

### Evolutionary Game Theory
- **Replicator Dynamics**: Simulate population dynamics and visualize trajectories
- **Evolutionary Stability**: Check if strategies are evolutionarily stable (ESS)
- **CFR Convergence**: Watch counterfactual regret minimization converge

### Game Visualization
- **Tree View**: Interactive extensive-form game trees with information sets
- **Matrix View**: Normal-form payoff matrices with equilibrium highlighting
- **Dual Views**: Switch between tree and matrix representations of the same game
- **Equilibrium Overlay**: See which strategies are played in each equilibrium

### Supported Game Formats
- **Extensive Form**: Sequential games with information sets (JSON, Gambit .efg)
- **Normal Form**: Strategic-form games as payoff matrices (JSON, Gambit .nfg)
- **MAID**: Multi-Agent Influence Diagrams for causal game models
- **Vegas DSL**: Compact text format for quick game specification

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for frontend)

### Running the Workbench

```bash
# Start the backend (builds on first run)
docker compose up -d

# Start the frontend
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 to use the workbench. Example games are pre-loaded.

## Example Games Included

| Game | Type | Highlights |
|------|------|------------|
| Prisoner's Dilemma | Normal form | Dominant strategy equilibrium |
| Battle of the Sexes | Normal form | Multiple equilibria, coordination |
| Matching Pennies | Normal form | Zero-sum, mixed equilibrium only |
| Rock-Paper-Scissors | Normal form | Symmetric, mixed equilibrium |
| Stag Hunt | Normal form | Payoff vs risk dominance |
| Trust Game | Extensive form | Sequential moves, backward induction |
| Centipede | Extensive form | Long horizon, SPE vs observed play |
| Signaling Game | Extensive form | Incomplete information, information sets |
| Monty Hall | Extensive form | Classic probability puzzle as a game |

## Analysis Plugins

The workbench uses specialized plugins for different analyses:

| Plugin | Capabilities |
|--------|--------------|
| **Gambit** | Nash equilibria (pure/mixed), IESDS, EFG/NFG parsing |
| **PyCID** | MAID Nash and SPE, causal influence diagrams |
| **OpenSpiel** | CFR convergence, exploitability measurement |
| **EGTTools** | Replicator dynamics, evolutionary stability |
| **Vegas** | Vegas DSL compilation and game parsing |

## Documentation

- [Game Formats](docs/GAME_FORMATS.md) — JSON, EFG, NFG, Vegas DSL specifications
- [API Reference](docs/API_REFERENCE.md) — REST API for programmatic access
- [Plugin Guide](docs/PLUGIN_GUIDE.md) — Extend with custom analyses
- [Architecture](docs/ARCHITECTURE.md) — System design overview

## Running Tests

```bash
# Backend tests
docker compose exec app pytest tests/ -v --tb=short --ignore=tests/integration

# Integration tests (all services must be running)
docker compose exec app pytest tests/integration/ -v --tb=short

# Frontend type check
cd frontend && npm run build
```

## Technology

- **Backend**: FastAPI + Docker Compose (Python analysis plugins)
- **Frontend**: React, Pixi.js (canvas), Zustand (state), TypeScript
- **Analysis Libraries**: pygambit, pycid, OpenSpiel, EGTTools

## License

MIT License — see [LICENSE](LICENSE) for details.
