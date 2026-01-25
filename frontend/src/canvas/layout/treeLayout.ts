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
  level: number;      // Tree depth (0 = root)
  sublevel: number;   // Info set layer at this level (0 = no offset)
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
const { nodeRadius: NODE_RADIUS, levelHeight: LEVEL_HEIGHT, minNodeSpacing: MIN_NODE_SPACING, infoSetSpacing: INFOSET_SPACING } = visualConfig.layout;

/**
 * Count nodes per info set (to identify singletons that don't need sublevel offsets).
 */
function countInfoSetNodes(game: Game, nodeId: string, counts: Map<string, number>): void {
  const node = game.nodes[nodeId];
  if (!node) return;

  if (node.information_set) {
    counts.set(node.information_set, (counts.get(node.information_set) || 0) + 1);
  }

  for (const action of node.actions) {
    if (action.target) {
      countInfoSetNodes(game, action.target, counts);
    }
  }
}

/**
 * Calculate positions for all nodes in the game tree.
 * Uses a simple recursive layout algorithm with info set sublevel layering.
 * Layout is calculated based on tree structure; viewport handles scaling.
 */
export function calculateLayout(game: Game): TreeLayout {
  const nodes = new Map<string, NodePosition>();
  const edges: EdgePosition[] = [];

  // Pre-pass: count nodes per info set (singletons don't need sublevel offsets)
  const infoSetNodeCounts = new Map<string, number>();
  countInfoSetNodes(game, game.root, infoSetNodeCounts);

  // First pass: calculate tree structure and widths
  const subtreeWidths = new Map<string, number>();
  calculateSubtreeWidths(game, game.root, subtreeWidths);

  // Calculate tree width based on structure
  const treeWidth = subtreeWidths.get(game.root) || MIN_NODE_SPACING;

  // Sublevel tracking for info set layering
  // Maps "level_infoSetId" to sublevel number
  const infosetSublevels = new Map<string, number>();
  // Count of sublevels at each tree level
  const numSublevels: number[] = [];

  // Second pass: assign positions (tree centered at its natural width)
  const startX = treeWidth / 2;
  const startY = NODE_RADIUS + 20;
  assignPositions(game, game.root, startX, startY, 0, subtreeWidths, nodes, edges, infosetSublevels, numSublevels, infoSetNodeCounts);

  // Third pass: apply info set sublevel Y offsets
  //
  // The base Y positions were calculated with fixed LEVEL_HEIGHT between levels.
  // For sublevel layering, we need to:
  // 1. Push deeper levels down to make room for sublevel space at earlier levels
  // 2. Offset nodes within each level based on their sublevel
  //
  // Key insight: The cumulative offset for level L must account for the FULL
  // sublevel range at each previous level (numSublevels[i] * SPACING, not just
  // (numSublevels[i]-1) * SPACING), because sublevel 1 nodes are at the base
  // and higher sublevels extend downward from there.

  // Find max level to ensure we cover all nodes
  let maxLevel = 0;
  for (const pos of nodes.values()) {
    maxLevel = Math.max(maxLevel, pos.level);
  }

  // Extend numSublevels to cover all levels
  while (numSublevels.length <= maxLevel) {
    numSublevels.push(0);
  }

  // Calculate cumulative extra space: at each level, we need space for ALL sublevels
  // cumulativeExtraSpace[L] = total extra space from levels 0..L-1
  const cumulativeExtraSpace: number[] = [0];
  for (let i = 0; i < maxLevel; i++) {
    // Space needed at level i = (number of sublevels at i) * SPACING
    // But sublevel 1 is at the "base", so we only need (numSublevels - 1) extra
    // However, ALL nodes at level i+1 need to clear the BOTTOM of level i
    const extraAtLevel = Math.max(0, numSublevels[i] || 0) * INFOSET_SPACING;
    cumulativeExtraSpace.push(cumulativeExtraSpace[i] + extraAtLevel);
  }

  // Apply Y offsets to all nodes
  for (const pos of nodes.values()) {
    // Add cumulative extra space from all previous levels
    const cumulative = cumulativeExtraSpace[pos.level] || 0;
    if (cumulative > 0) {
      pos.y += cumulative;
    }

    // Offset within this level based on sublevel (sublevel 1 at top, others below)
    if (pos.sublevel > 1) {
      pos.y += (pos.sublevel - 1) * INFOSET_SPACING;
    }
  }

  // Update edge positions to match node offsets
  for (const edge of edges) {
    const fromNode = nodes.get(edge.fromId);
    const toNode = nodes.get(edge.toId);
    if (fromNode) {
      edge.fromX = fromNode.x;
      edge.fromY = fromNode.y;
    }
    if (toNode) {
      edge.toX = toNode.x;
      edge.toY = toNode.y;
    }
  }

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

/**
 * Get or assign a sublevel for an info set at a given tree level.
 * Same info set at the same level gets the same sublevel.
 * Different info sets at the same level get incrementing sublevels.
 * Singleton info sets (only one node) return 0 - no sublevel offset needed.
 */
function getOrAssignSublevel(
  level: number,
  infoSetId: string | undefined,
  infosetSublevels: Map<string, number>,
  numSublevels: number[],
  infoSetNodeCounts: Map<string, number>
): number {
  if (!infoSetId) return 0;

  // Singleton info sets don't need sublevel offsets (no enclosure overlap possible)
  if ((infoSetNodeCounts.get(infoSetId) || 0) < 2) return 0;

  const key = `${level}_${infoSetId}`;
  if (infosetSublevels.has(key)) {
    return infosetSublevels.get(key)!;
  }

  // Extend numSublevels array if needed
  while (numSublevels.length <= level) {
    numSublevels.push(0);
  }

  // Assign new sublevel
  const sublevel = ++numSublevels[level];
  infosetSublevels.set(key, sublevel);
  return sublevel;
}

function assignPositions(
  game: Game,
  nodeId: string,
  centerX: number,
  y: number,
  level: number,
  subtreeWidths: Map<string, number>,
  nodes: Map<string, NodePosition>,
  edges: EdgePosition[],
  infosetSublevels: Map<string, number>,
  numSublevels: number[],
  infoSetNodeCounts: Map<string, number>
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
      level,
      sublevel: 0,
    });
    return;
  }

  const node = game.nodes[nodeId];
  if (!node) return;

  // Get sublevel for this node's info set (singletons return 0)
  const sublevel = getOrAssignSublevel(level, node.information_set, infosetSublevels, numSublevels, infoSetNodeCounts);

  // Add this node
  nodes.set(nodeId, {
    id: nodeId,
    x: centerX,
    y,
    type: 'decision',
    player: node.player,
    informationSet: node.information_set,
    level,
    sublevel,
  });

  // Calculate child positions
  const totalWidth = subtreeWidths.get(nodeId) || MIN_NODE_SPACING;
  let currentX = centerX - totalWidth / 2;

  for (const action of node.actions) {
    if (!action.target) continue;

    const childWidth = subtreeWidths.get(action.target) || MIN_NODE_SPACING;
    const childX = currentX + childWidth / 2;
    const childY = y + LEVEL_HEIGHT;

    // Add edge (positions will be updated after offset application)
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

    // Recurse with incremented level
    assignPositions(game, action.target, childX, childY, level + 1, subtreeWidths, nodes, edges, infosetSublevels, numSublevels, infoSetNodeCounts);

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
