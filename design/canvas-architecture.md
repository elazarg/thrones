# Canvas Module Architecture

> **Note**: This document describes the intended architecture and serves as a starting point for understanding the codebase. The source code in `frontend/src/canvas/` is the authoritative reference. This documentation may become stale as the code evolves.

## Overview

The canvas module provides game tree visualization using Pixi.js. It separates concerns into distinct layers that can be developed, tested, and extended independently.

```
┌─────────────────────────────────────────────────────────────┐
│                    GameCanvas Component                      │
│  Thin React wrapper - stores, layout, render orchestration  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      useCanvas Hook                          │
│  Pixi lifecycle, viewport, rendering orchestration          │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Layout    │    │   TreeRenderer   │    │ OverlayManager  │
│  treeLayout │    │  + Elements      │    │ + Overlays      │
└─────────────┘    └──────────────────┘    └─────────────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      VisualConfig                            │
│  Centralized constants for all visual styling               │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
frontend/src/canvas/
├── config/
│   └── visualConfig.ts      # All visual constants (colors, sizes, spacing)
├── core/
│   └── sceneGraph.ts        # Pixi.js container/layer management (for future use)
├── layout/
│   └── treeLayout.ts        # Pure layout calculation (positions from game data)
├── renderers/
│   ├── TreeRenderer.ts      # Orchestrates element rendering
│   ├── types.ts             # Renderer interfaces
│   └── elements/
│       ├── DecisionNode.ts  # Circle nodes with player labels
│       ├── OutcomeNode.ts   # Square nodes with payoff labels
│       ├── Edge.ts          # Lines with action labels, dominated styling
│       └── InfoSetEnclosure.ts  # Dashed rectangles grouping info sets
├── overlays/
│   ├── types.ts             # Overlay interface
│   ├── OverlayManager.ts    # Coordinates overlay lifecycle
│   └── EquilibriumOverlay.ts # Star markers on equilibrium outcomes
├── hooks/
│   ├── useCanvas.ts         # Main composition hook (Pixi + render + overlays)
│   ├── useLayout.ts         # Memoized layout calculation
│   ├── useSceneGraph.ts     # Scene lifecycle (for future use)
│   └── useOverlays.ts       # Overlay management
└── index.ts                 # Public API exports
```

## Key Concepts

### 1. Visual Configuration (`config/visualConfig.ts`)

All visual constants are centralized in a single static object. This eliminates magic numbers scattered throughout the codebase.

```typescript
export const visualConfig = {
  node: { decisionRadius: 20, outcomeSize: 16, strokeWidth: 2, ... },
  edge: { width: 2, color: 0x30363d, dominatedAlpha: 0.3, ... },
  layout: { levelHeight: 100, minNodeSpacing: 80, padding: 60, ... },
  playerColors: [0x1f6feb, 0x8b5cf6, 0x10b981, 0xf59e0b],
  // ... more settings
} as const;
```

**Design decision**: This is a plain object, not a Zustand store. Visual config rarely changes at runtime, and a static object is simpler. Reactivity can be added later if needed.

### 2. Layout Engine (`layout/treeLayout.ts`)

The layout engine computes node and edge positions from game data. It is a pure function with no side effects.

```typescript
interface TreeLayout {
  nodes: Map<string, NodePosition>;
  edges: EdgePosition[];
  width: number;
  height: number;
}

function calculateLayout(game: Game): TreeLayout
```

Layout includes:
- Node positions (x, y) calculated using a tree algorithm
- Node metadata (type, player, payoffs, information set)
- Edge positions and labels
- Dominated action warnings (from game.dominatedActions)

**Key insight**: The layout includes analysis data (dominated actions) from the game model. This is intentional—the layout represents everything needed to render the base visualization.

### 3. Element Renderers (`renderers/elements/`)

Each visual element has a dedicated renderer function:

```typescript
// DecisionNode.ts
function renderDecisionNode(
  container: Container,
  nodeId: string,
  pos: NodePosition,
  players: string[],
  config: VisualConfig,
  onHover?: (nodeId: string | null) => void
): void

// Edge.ts
function renderEdge(
  container: Container,
  edge: EdgePosition,
  config: VisualConfig,
  options?: { dominated?: boolean }
): void
```

Element renderers:
- Take a Pixi Container and draw into it
- Use VisualConfig for all styling
- Are stateless and side-effect free (except Pixi graphics)
- Handle their own interactivity (hover events)

### 4. Tree Renderer (`renderers/TreeRenderer.ts`)

TreeRenderer composes element renderers to draw a complete game tree:

```typescript
class TreeRenderer implements TreeRendererInterface {
  render(container, game, layout, context): void {
    // 1. Info set enclosures (behind everything)
    this.renderInfoSets(container, layout, config);

    // 2. Edges (including dominated styling from layout.edges[].warning)
    this.renderEdges(container, layout, config);

    // 3. Nodes (on top)
    this.renderNodes(container, layout, players, config, onHover);
  }
}
```

TreeRenderer handles the **base visualization**—the game structure as defined by the game model. It does not handle analysis overlays like equilibrium highlighting.

### 5. Overlays (`overlays/`)

Overlays add visual elements for analysis results. They are separate from base rendering so:
- New analyses can add visualizations without modifying TreeRenderer
- Overlays can be toggled on/off independently
- Different analyses don't conflict visually

```typescript
interface Overlay {
  id: string;
  zIndex: number;

  // Compute what to display from context
  compute(context: OverlayContext): OverlayData | null;

  // Add graphics to the container
  apply(container: Container, data: OverlayData, config: VisualConfig): void;

  // Remove graphics
  clear(container: Container): void;
}
```

**OverlayContext** includes:
- Game and layout data
- Analysis results from the store
- Selected equilibrium (UI state)

**Current overlays**:
- `EquilibriumOverlay`: Adds star markers to equilibrium outcome nodes

**Future overlays** (not yet implemented):
- `SelectionOverlay`: Hover/selection highlights
- `SimulationOverlay`: Animated path highlighting during simulation
- `BeliefOverlay`: Probability badges at information sets

### 6. useCanvas Hook (`hooks/useCanvas.ts`)

The main composition hook that orchestrates everything:

```typescript
function useCanvas(options: UseCanvasOptions): UseCanvasReturn {
  // 1. Initialize Pixi Application
  // 2. Prevent browser zoom (ctrl+wheel goes to viewport)
  // 3. Create viewport for pan/zoom
  // 4. Calculate layout from game
  // 5. Render tree using TreeRenderer
  // 6. Apply overlays using OverlayManager
  // 7. Fit viewport to content
}
```

The component just calls this hook and renders UI:

```typescript
function GameCanvas() {
  const { containerRef, fitToView } = useCanvas({ game, results, ... });
  return <div ref={containerRef}>...</div>;
}
```

## Data Flow

```
Game Store ─────────────────────────────────────────────────────►
                │
                ▼
         calculateLayout(game)
                │
                ▼
┌───────────────────────────────────┐
│          TreeLayout               │
│  - nodes: Map<id, NodePosition>   │
│  - edges: EdgePosition[]          │
│  - width, height                  │
└───────────────────────────────────┘
                │
                ├─────────────────────────────────────┐
                ▼                                     ▼
┌─────────────────────────┐            ┌─────────────────────────┐
│     TreeRenderer        │            │    OverlayManager       │
│  renderInfoSets()       │            │  + EquilibriumOverlay   │
│  renderEdges()          │            │    compute()            │
│  renderNodes()          │            │    apply()              │
└─────────────────────────┘            └─────────────────────────┘
                │                                     │
                └─────────────┬───────────────────────┘
                              ▼
                     Pixi.js Container
                              │
                              ▼
                      Canvas Display
```

## Extension Points

### Adding a New Overlay

1. Create `overlays/MyOverlay.ts` implementing the `Overlay` interface
2. Register it in `overlays/OverlayManager.ts` → `createDefaultOverlayManager()`
3. The overlay will automatically receive context and render when appropriate

Example:
```typescript
// overlays/SimulationOverlay.ts
export class SimulationOverlay implements Overlay {
  id = 'simulation';
  zIndex = 150;

  compute(context) {
    // Return path data if simulation is running
  }

  apply(container, data, config) {
    // Highlight the simulation path
  }
}
```

### Adding a New Element Type

1. Create `renderers/elements/MyElement.ts` with a render function
2. Call it from `TreeRenderer` at the appropriate z-order position

### Supporting New Game Formats

The renderer is format-agnostic. The `TreeLayout` interface is the contract:
- Any game format that can produce a tree structure works
- Non-tree formats (DAG, matrix) would need different renderers

Future architecture allows:
```typescript
interface Renderer<TData, TLayout> {
  calculateLayout(data: TData): TLayout;
  render(container, data, layout, context): void;
}

// Different implementations:
// - TreeRenderer for extensive form games
// - DAGRenderer for MAIDs
// - MatrixRenderer for normal form
```

## Design Decisions

### Why static visualConfig instead of a store?

Visual styling rarely changes at runtime. A static object is:
- Simpler (no subscriptions, no re-renders)
- Type-safe with `as const`
- Easy to override for theming later

### Why include dominated actions in layout?

The layout represents "everything the base renderer needs." Dominated actions come from game analysis but are rendered as part of the tree (faded edges, warning icons). This keeps TreeRenderer stateless—it just reads positions and renders.

### Why separate overlays from base rendering?

Overlays depend on **UI state** (selected equilibrium) and **computed results** (analysis store). The base tree only depends on **game data**. This separation:
- Allows overlays to update without re-rendering the entire tree
- Prevents analysis code from coupling with rendering code
- Makes it easy to add new analysis visualizations

### Why useCanvas instead of useSceneGraph + useOverlays separately?

For now, `useCanvas` is a simple composition. As complexity grows, we may split it. The hooks exist individually for future use:
- `useSceneGraph`: Full scene management with named layers
- `useOverlays`: Just overlay lifecycle

## Testing Strategy

Each layer can be tested independently:

- **visualConfig**: Static object, no tests needed
- **treeLayout**: Pure function, unit tests with sample games
- **Element renderers**: Can mock Container, verify graphics calls
- **TreeRenderer**: Integration tests with mock containers
- **Overlays**: Test compute() logic separately from apply()
- **useCanvas**: React Testing Library with Pixi.js mock

## Known Limitations

1. **No scene graph usage yet**: `SceneGraph` class exists but `useCanvas` creates containers directly. Planned for Phase 7+.

2. **Viewport recreation on render**: Currently destroys and recreates viewport on each render. Could optimize to reuse.

3. **Single overlay manager per canvas**: Can't have multiple independent overlay sets. Fine for now.

4. **No caching**: Layout recalculates on every game change. Could memoize subtrees for large games.

## References

- Product design: `design/gambit-canvas-design.md`
- Tech stack: `design/gambit-tech-stack.md`
- Implementation: `frontend/src/canvas/`
