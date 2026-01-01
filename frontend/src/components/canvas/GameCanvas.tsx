import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { Application, Container, Graphics, Text, TextStyle } from 'pixi.js';
import { useGameStore, useAnalysisStore, useUIStore } from '../../stores';
import { calculateLayout, getPlayerColor } from '../../lib/treeLayout';
import type { NodePosition, EdgePosition } from '../../lib/treeLayout';
import type { NashEquilibrium } from '../../types';
import './GameCanvas.css';

const NODE_RADIUS = 20;
const OUTCOME_SIZE = 16;

export function GameCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const [isReady, setIsReady] = useState(false);

  const game = useGameStore((state) => state.game);
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
    return calculateLayout(game, 600);
  }, [game]);

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

    const container = new Container();
    app.stage.addChild(container);

    // Center the tree
    const offsetX = Math.max(0, (app.screen.width - layout.width) / 2);
    const offsetY = 40;
    container.x = offsetX;
    container.y = offsetY;

    // Draw edges first (so nodes are on top)
    for (const edge of layout.edges) {
      drawEdge(container, edge, game.players, selectedEquilibrium);
    }

    // Draw nodes
    for (const [nodeId, pos] of layout.nodes) {
      drawNode(container, nodeId, pos, game.players, setHoveredNode);
    }
  }, [layout, game, selectedEquilibrium, setHoveredNode]);

  useEffect(() => {
    if (isReady) {
      renderTree();
    }
  }, [isReady, renderTree]);

  return (
    <div className="game-canvas" ref={containerRef}>
      {!game && <div className="canvas-loading">Loading game...</div>}
    </div>
  );
}

function drawEdge(
  container: Container,
  edge: EdgePosition,
  players: string[],
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
  onHover: (id: string | null) => void
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
