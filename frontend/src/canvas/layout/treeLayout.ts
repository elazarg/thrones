import type { Game } from '../../types';
import { visualConfig } from '../config/visualConfig';

export interface NodePosition {
  id: string;
  x: number;
  y: number;
  type: 'decision' | 'outcome';
  player?: string;
  label?: string;
  payoffs?: Record<string, number>;
  informationSet?: string;
}

export interface EdgePosition {
  fromId: string;
  toId: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  label: string;
  warning?: string;
}

export interface TreeLayout {
  nodes: Map<string, NodePosition>;
  edges: EdgePosition[];
  width: number;
  height: number;
}

// Use layout config values
const { nodeRadius: NODE_RADIUS, levelHeight: LEVEL_HEIGHT, minNodeSpacing: MIN_NODE_SPACING } = visualConfig.layout;

/**
 * Calculate positions for all nodes in the game tree.
 * Uses a simple recursive layout algorithm.
 * Layout is calculated based on tree structure; viewport handles scaling.
 */
export function calculateLayout(game: Game): TreeLayout {
  const nodes = new Map<string, NodePosition>();
  const edges: EdgePosition[] = [];

  // First pass: calculate tree structure and widths
  const subtreeWidths = new Map<string, number>();
  calculateSubtreeWidths(game, game.root, subtreeWidths);

  // Calculate tree width based on structure
  const treeWidth = subtreeWidths.get(game.root) || MIN_NODE_SPACING;

  // Second pass: assign positions (tree centered at its natural width)
  const startX = treeWidth / 2;
  const startY = NODE_RADIUS + 20;
  assignPositions(game, game.root, startX, startY, subtreeWidths, nodes, edges);

  // Calculate actual bounds from node positions
  let minX = Infinity;
  let maxX = 0;
  let maxY = 0;
  for (const pos of nodes.values()) {
    minX = Math.min(minX, pos.x - NODE_RADIUS);
    maxX = Math.max(maxX, pos.x + NODE_RADIUS);
    maxY = Math.max(maxY, pos.y + NODE_RADIUS);
  }

  return {
    nodes,
    edges,
    width: maxX + 20,
    height: maxY + 40,
  };
}

function calculateSubtreeWidths(
  game: Game,
  nodeId: string,
  widths: Map<string, number>
): number {
  // Check if it's an outcome
  if (game.outcomes[nodeId]) {
    widths.set(nodeId, MIN_NODE_SPACING);
    return MIN_NODE_SPACING;
  }

  const node = game.nodes[nodeId];
  if (!node) {
    widths.set(nodeId, MIN_NODE_SPACING);
    return MIN_NODE_SPACING;
  }

  let totalWidth = 0;
  for (const action of node.actions) {
    if (action.target) {
      totalWidth += calculateSubtreeWidths(game, action.target, widths);
    }
  }

  const width = Math.max(totalWidth, MIN_NODE_SPACING);
  widths.set(nodeId, width);
  return width;
}

function assignPositions(
  game: Game,
  nodeId: string,
  centerX: number,
  y: number,
  subtreeWidths: Map<string, number>,
  nodes: Map<string, NodePosition>,
  edges: EdgePosition[]
): void {
  // Check if it's an outcome
  const outcome = game.outcomes[nodeId];
  if (outcome) {
    nodes.set(nodeId, {
      id: nodeId,
      x: centerX,
      y,
      type: 'outcome',
      label: outcome.label,
      payoffs: outcome.payoffs,
    });
    return;
  }

  const node = game.nodes[nodeId];
  if (!node) return;

  // Add this node
  nodes.set(nodeId, {
    id: nodeId,
    x: centerX,
    y,
    type: 'decision',
    player: node.player,
    informationSet: node.information_set,
  });

  // Calculate child positions
  const totalWidth = subtreeWidths.get(nodeId) || MIN_NODE_SPACING;
  let currentX = centerX - totalWidth / 2;

  for (const action of node.actions) {
    if (!action.target) continue;

    const childWidth = subtreeWidths.get(action.target) || MIN_NODE_SPACING;
    const childX = currentX + childWidth / 2;
    const childY = y + LEVEL_HEIGHT;

    // Add edge
    edges.push({
      fromId: nodeId,
      toId: action.target,
      fromX: centerX,
      fromY: y,
      toX: childX,
      toY: childY,
      label: action.label,
      warning: action.warning,
    });

    // Recurse
    assignPositions(game, action.target, childX, childY, subtreeWidths, nodes, edges);

    currentX += childWidth;
  }
}

/**
 * Get color for a player.
 */
export function getPlayerColor(player: string, players: string[]): number {
  const index = players.indexOf(player);
  return visualConfig.playerColors[index % visualConfig.playerColors.length];
}
