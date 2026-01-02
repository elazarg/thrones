import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { Application, Container, Graphics, Text, TextStyle } from 'pixi.js';
import { Viewport } from 'pixi-viewport';
import { useGameStore, useAnalysisStore, useUIStore } from '../../stores';
import { calculateLayout, getPlayerColor } from '../../lib/treeLayout';
import type { NodePosition, EdgePosition } from '../../lib/treeLayout';
import type { NashEquilibrium } from '../../types';
import './GameCanvas.css';

const NODE_RADIUS = 20;
const OUTCOME_SIZE = 16;
const PADDING = 60;

/** Check if two payoff objects match (for equilibrium detection). */
function isMatchingPayoffs(
  outcomePayoffs: Record<string, number>,
  equilibriumPayoffs: Record<string, number>
): boolean {
  const players = Object.keys(equilibriumPayoffs);
  return players.every(
    (player) => Math.abs((outcomePayoffs[player] ?? 0) - equilibriumPayoffs[player]) < 0.001
  );
}

export function GameCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const viewportRef = useRef<Viewport | null>(null);
  const [isReady, setIsReady] = useState(false);

  const game = useGameStore((state) => state.currentGame);
  const gameLoading = useGameStore((state) => state.gameLoading);
  const results = useAnalysisStore((state) => state.results);
  const selectedEqIndex = useAnalysisStore((state) => state.selectedEquilibriumIndex);
  const setHoveredNode = useUIStore((state) => state.setHoveredNode);

  // Get selected equilibrium if any
  const selectedEquilibrium = useMemo(() => {
    if (selectedEqIndex === null) return null;
    for (const result of results) {
      const eqs = result.details.equilibria;
      if (eqs && eqs[selectedEqIndex]) {
        return eqs[selectedEqIndex];
      }
    }
    return null;
  }, [results, selectedEqIndex]);

  // Calculate layout when game changes
  const layout = useMemo(() => {
    if (!game) return null;
    return calculateLayout(game);
  }, [game]);

  // Prevent browser zoom on canvas (pinch/ctrl+wheel should only zoom the viewport)
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const preventZoom = (e: WheelEvent) => {
      if (e.ctrlKey) {
        e.preventDefault();
      }
    };

    const preventTouchZoom = (e: TouchEvent) => {
      if (e.touches.length > 1) {
        e.preventDefault();
      }
    };

    container.addEventListener('wheel', preventZoom, { passive: false });
    container.addEventListener('touchmove', preventTouchZoom, { passive: false });

    return () => {
      container.removeEventListener('wheel', preventZoom);
      container.removeEventListener('touchmove', preventTouchZoom);
    };
  }, []);

  // Initialize Pixi application
  useEffect(() => {
    if (!containerRef.current) return;

    let cancelled = false;
    const app = new Application();

    const initApp = async () => {
      try {
        await app.init({
          background: 0x0d1117,
          resizeTo: containerRef.current!,
          antialias: true,
          resolution: window.devicePixelRatio || 1,
          autoDensity: true,
        });

        if (cancelled) {
          app.destroy(true);
          return;
        }

        containerRef.current!.appendChild(app.canvas);
        appRef.current = app;
        setIsReady(true);
      } catch (err) {
        console.error('Failed to initialize Pixi:', err);
      }
    };

    initApp();

    return () => {
      cancelled = true;
      setIsReady(false);
      if (viewportRef.current) {
        viewportRef.current.destroy();
        viewportRef.current = null;
      }
      if (appRef.current) {
        appRef.current.destroy(true, { children: true });
        appRef.current = null;
      }
    };
  }, []);

  // Render game tree - only when app is ready
  const renderTree = useCallback(() => {
    const app = appRef.current;
    if (!app || !app.stage || !layout || !game) return;

    // Clear previous content
    app.stage.removeChildren();
    if (viewportRef.current) {
      viewportRef.current.destroy();
      viewportRef.current = null;
    }

    // Create viewport for zoom/pan
    const viewport = new Viewport({
      screenWidth: app.screen.width,
      screenHeight: app.screen.height,
      worldWidth: layout.width + PADDING * 2,
      worldHeight: layout.height + PADDING * 2,
      events: app.renderer.events,
    });

    // Enable interactions
    viewport
      .drag()
      .pinch({ percent: 3 })
      .wheel({ percent: 0.15, smooth: 5 })
      .decelerate({ friction: 0.92 });

    app.stage.addChild(viewport);
    viewportRef.current = viewport;

    // Create container for tree content
    const container = new Container();
    container.x = PADDING;
    container.y = PADDING;
    viewport.addChild(container);

    // Draw edges first (so nodes are on top)
    for (const edge of layout.edges) {
      drawEdge(container, edge, selectedEquilibrium);
    }

    // Draw nodes
    for (const [nodeId, pos] of layout.nodes) {
      drawNode(container, nodeId, pos, game.players, setHoveredNode, selectedEquilibrium);
    }

    // Fit the tree to the viewport
    viewport.fit(true, layout.width + PADDING * 2, layout.height + PADDING * 2);
    viewport.moveCenter(
      (layout.width + PADDING * 2) / 2,
      (layout.height + PADDING * 2) / 2
    );
  }, [layout, game, selectedEquilibrium, setHoveredNode]);

  useEffect(() => {
    if (isReady) {
      renderTree();
    }
  }, [isReady, renderTree]);

  // Handle fit to view
  const handleFitToView = useCallback(() => {
    if (viewportRef.current && layout) {
      viewportRef.current.fit(true, layout.width + PADDING * 2, layout.height + PADDING * 2);
      viewportRef.current.moveCenter(
        (layout.width + PADDING * 2) / 2,
        (layout.height + PADDING * 2) / 2
      );
    }
  }, [layout]);

  return (
    <div className="game-canvas" ref={containerRef}>
      {gameLoading && <div className="canvas-loading">Loading game...</div>}
      {!game && !gameLoading && (
        <div className="canvas-empty">
          <p>No game selected</p>
          <p className="hint">Upload a .efg or .json file to get started</p>
        </div>
      )}
      {game && !gameLoading && (
        <div className="canvas-controls">
          <button className="fit-button" onClick={handleFitToView} title="Fit to view">
            ⊡
          </button>
        </div>
      )}
    </div>
  );
}

function drawEdge(
  container: Container,
  edge: EdgePosition,
  equilibrium: NashEquilibrium | null
): void {
  const graphics = new Graphics();

  // Determine line thickness based on equilibrium probability
  const thickness = 2;
  let alpha = 1;

  if (equilibrium && edge.warning) {
    // Dominated strategy - fade it
    alpha = 0.3;
  }

  // Draw the edge line
  graphics
    .moveTo(edge.fromX, edge.fromY + NODE_RADIUS)
    .lineTo(edge.toX, edge.toY - NODE_RADIUS)
    .stroke({ width: thickness, color: 0x30363d, alpha });

  container.addChild(graphics);

  // Draw action label
  const midX = (edge.fromX + edge.toX) / 2;
  const midY = (edge.fromY + edge.toY) / 2;

  const labelStyle = new TextStyle({
    fontFamily: 'Inter, system-ui, sans-serif',
    fontSize: 12,
    fill: edge.warning ? 0x8b949e : 0x7ee0ff,
    fontStyle: edge.warning ? 'italic' : 'normal',
  });

  const label = new Text({ text: edge.label, style: labelStyle });
  label.anchor.set(0.5, 0.5);
  label.x = midX + 20;
  label.y = midY;
  label.alpha = alpha;
  container.addChild(label);

  // Draw warning icon if present
  if (edge.warning) {
    const warningStyle = new TextStyle({
      fontFamily: 'Inter, system-ui, sans-serif',
      fontSize: 10,
      fill: 0xf0a93b,
    });
    const warning = new Text({ text: '⚠', style: warningStyle });
    warning.anchor.set(0.5, 0.5);
    warning.x = midX + 20;
    warning.y = midY + 14;
    warning.alpha = 0.7;
    container.addChild(warning);
  }
}

function drawNode(
  container: Container,
  nodeId: string,
  pos: NodePosition,
  players: string[],
  onHover: (id: string | null) => void,
  equilibrium: NashEquilibrium | null
): void {
  const graphics = new Graphics();

  if (pos.type === 'decision') {
    // Draw decision node as circle
    const color = pos.player ? getPlayerColor(pos.player, players) : 0x1f6feb;
    graphics
      .circle(pos.x, pos.y, NODE_RADIUS)
      .fill({ color, alpha: 0.8 })
      .stroke({ width: 2, color: 0xe6edf3, alpha: 0.5 });

    // Player label
    if (pos.player) {
      const style = new TextStyle({
        fontFamily: 'Inter, system-ui, sans-serif',
        fontSize: 11,
        fill: 0xe6edf3,
        fontWeight: 'bold',
      });
      const text = new Text({ text: pos.player, style });
      text.anchor.set(0.5, 0.5);
      text.x = pos.x;
      text.y = pos.y;
      container.addChild(text);
    }
  } else {
    // Draw outcome node as square
    graphics
      .rect(pos.x - OUTCOME_SIZE, pos.y - OUTCOME_SIZE, OUTCOME_SIZE * 2, OUTCOME_SIZE * 2)
      .fill({ color: 0x161b22 })
      .stroke({ width: 2, color: 0x8df4a3, alpha: 0.8 });

    // Equilibrium star marker
    if (equilibrium && pos.payoffs) {
      const isEquilibriumOutcome = isMatchingPayoffs(pos.payoffs, equilibrium.payoffs);
      if (isEquilibriumOutcome) {
        const starStyle = new TextStyle({
          fontFamily: 'Inter, system-ui, sans-serif',
          fontSize: 16,
          fill: 0xffd700,  // Gold
        });
        const star = new Text({ text: '★', style: starStyle });
        star.anchor.set(0.5, 1);
        star.x = pos.x;
        star.y = pos.y - OUTCOME_SIZE - 4;
        container.addChild(star);
      }
    }

    // Outcome label
    if (pos.label) {
      const style = new TextStyle({
        fontFamily: 'Inter, system-ui, sans-serif',
        fontSize: 10,
        fill: 0x8df4a3,
      });
      const text = new Text({ text: pos.label, style });
      text.anchor.set(0.5, 0);
      text.x = pos.x;
      text.y = pos.y + OUTCOME_SIZE + 4;
      container.addChild(text);
    }
  }

  // Make interactive
  graphics.eventMode = 'static';
  graphics.cursor = 'pointer';
  graphics.on('pointerover', () => onHover(nodeId));
  graphics.on('pointerout', () => onHover(null));

  container.addChild(graphics);
}
