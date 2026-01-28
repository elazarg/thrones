import type { MAIDGame, MAIDNode, MAIDEdge } from '../../types';
import { visualConfig } from '../config/visualConfig';

export interface MAIDNodePosition {
  id: string;
  x: number;
  y: number;
  type: 'decision' | 'utility' | 'chance';
  agent?: string;
  label: string;
  layer: number;
}

export interface MAIDEdgePosition {
  sourceId: string;
  targetId: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
}

export interface MAIDLayout {
  nodes: Map<string, MAIDNodePosition>;
  edges: MAIDEdgePosition[];
  width: number;
  height: number;
}

const { maid: maidConfig } = visualConfig;

/**
 * Build adjacency list for topological sort.
 */
function buildAdjacencyList(edges: MAIDEdge[]): Map<string, string[]> {
  const adj = new Map<string, string[]>();
  for (const edge of edges) {
    const children = adj.get(edge.source) || [];
    children.push(edge.target);
    adj.set(edge.source, children);
  }
  return adj;
}

/**
 * Build reverse adjacency list (parents for each node).
 */
function buildReverseAdjacencyList(edges: MAIDEdge[]): Map<string, string[]> {
  const adj = new Map<string, string[]>();
  for (const edge of edges) {
    const parents = adj.get(edge.target) || [];
    parents.push(edge.source);
    adj.set(edge.target, parents);
  }
  return adj;
}

/**
 * Calculate layer for each node using longest path from roots.
 * This ensures edges generally point downward.
 */
function assignLayers(
  nodes: MAIDNode[],
  edges: MAIDEdge[]
): Map<string, number> {
  const layers = new Map<string, number>();
  const adj = buildAdjacencyList(edges);
  const reverseAdj = buildReverseAdjacencyList(edges);

  // Find root nodes (no incoming edges)
  const nodeIds = new Set(nodes.map(n => n.id));
  const hasParent = new Set(edges.map(e => e.target));
  const roots: string[] = [];
  for (const id of nodeIds) {
    if (!hasParent.has(id)) {
      roots.push(id);
    }
  }

  // BFS to assign layers based on longest path from any root
  // Use reverse topological order for correct longest path calculation
  const inDegree = new Map<string, number>();
  for (const node of nodes) {
    const parents = reverseAdj.get(node.id) || [];
    inDegree.set(node.id, parents.length);
  }

  // Initialize roots at layer 0
  const queue: string[] = [...roots];
  for (const root of roots) {
    layers.set(root, 0);
  }

  // Process in topological order
  while (queue.length > 0) {
    const current = queue.shift()!;
    const currentLayer = layers.get(current) || 0;

    const children = adj.get(current) || [];
    for (const child of children) {
      // Child layer is max of (current layer + 1) or existing
      const existingLayer = layers.get(child) || 0;
      layers.set(child, Math.max(existingLayer, currentLayer + 1));

      // Decrement in-degree, add to queue when all parents processed
      const deg = (inDegree.get(child) || 1) - 1;
      inDegree.set(child, deg);
      if (deg === 0) {
        queue.push(child);
      }
    }
  }

  // Handle disconnected nodes (shouldn't happen in valid MAID)
  for (const node of nodes) {
    if (!layers.has(node.id)) {
      layers.set(node.id, 0);
    }
  }

  return layers;
}

/**
 * Barycenter heuristic for node ordering within a layer.
 * Minimizes edge crossings by positioning nodes based on average position of connected nodes.
 */
function orderNodesInLayers(
  nodes: MAIDNode[],
  edges: MAIDEdge[],
  layers: Map<string, number>
): Map<number, MAIDNode[]> {
  // Group nodes by layer
  const layerNodes = new Map<number, MAIDNode[]>();
  let maxLayer = 0;

  for (const node of nodes) {
    const layer = layers.get(node.id) || 0;
    maxLayer = Math.max(maxLayer, layer);
    const nodesInLayer = layerNodes.get(layer) || [];
    nodesInLayer.push(node);
    layerNodes.set(layer, nodesInLayer);
  }

  // Build adjacency for barycenter calculation
  const reverseAdj = buildReverseAdjacencyList(edges);
  const forwardAdj = buildAdjacencyList(edges);

  // Multiple passes to stabilize ordering
  for (let pass = 0; pass < 3; pass++) {
    // Forward pass: order based on parents
    for (let layer = 1; layer <= maxLayer; layer++) {
      const nodesInLayer = layerNodes.get(layer) || [];
      const prevLayer = layerNodes.get(layer - 1) || [];

      // Calculate barycenter for each node
      const barycenters: { node: MAIDNode; center: number }[] = [];
      for (const node of nodesInLayer) {
        const parents = reverseAdj.get(node.id) || [];
        let sum = 0;
        let count = 0;
        for (const parentId of parents) {
          const parentIdx = prevLayer.findIndex(n => n.id === parentId);
          if (parentIdx >= 0) {
            sum += parentIdx;
            count++;
          }
        }
        const center = count > 0 ? sum / count : nodesInLayer.indexOf(node);
        barycenters.push({ node, center });
      }

      // Sort by barycenter
      barycenters.sort((a, b) => a.center - b.center);
      layerNodes.set(layer, barycenters.map(b => b.node));
    }

    // Backward pass: order based on children
    for (let layer = maxLayer - 1; layer >= 0; layer--) {
      const nodesInLayer = layerNodes.get(layer) || [];
      const nextLayer = layerNodes.get(layer + 1) || [];

      const barycenters: { node: MAIDNode; center: number }[] = [];
      for (const node of nodesInLayer) {
        const children = forwardAdj.get(node.id) || [];
        let sum = 0;
        let count = 0;
        for (const childId of children) {
          const childIdx = nextLayer.findIndex(n => n.id === childId);
          if (childIdx >= 0) {
            sum += childIdx;
            count++;
          }
        }
        const center = count > 0 ? sum / count : nodesInLayer.indexOf(node);
        barycenters.push({ node, center });
      }

      barycenters.sort((a, b) => a.center - b.center);
      layerNodes.set(layer, barycenters.map(b => b.node));
    }
  }

  return layerNodes;
}

/**
 * Calculate MAID layout using Sugiyama-style layered DAG algorithm.
 */
export function calculateMAIDLayout(game: MAIDGame): MAIDLayout {
  const nodes = new Map<string, MAIDNodePosition>();
  const edges: MAIDEdgePosition[] = [];

  // Step 1: Assign layers
  const layers = assignLayers(game.nodes, game.edges);

  // Step 2: Order nodes within layers
  const layerNodes = orderNodesInLayers(game.nodes, game.edges, layers);

  // Step 3: Calculate positions
  let maxWidth = 0;
  let maxHeight = 0;

  // Find max nodes in any layer for width calculation
  let maxNodesInLayer = 1;
  for (const nodesInLayer of layerNodes.values()) {
    maxNodesInLayer = Math.max(maxNodesInLayer, nodesInLayer.length);
  }

  const totalWidth = maxNodesInLayer * maidConfig.minNodeSpacing;

  for (const [layer, nodesInLayer] of layerNodes) {
    const y = layer * maidConfig.layerHeight + maidConfig.decisionRadius + 40;
    const layerWidth = nodesInLayer.length * maidConfig.minNodeSpacing;
    const startX = (totalWidth - layerWidth) / 2 + maidConfig.minNodeSpacing / 2;

    for (let i = 0; i < nodesInLayer.length; i++) {
      const node = nodesInLayer[i];
      const x = startX + i * maidConfig.minNodeSpacing;

      nodes.set(node.id, {
        id: node.id,
        x,
        y,
        type: node.type,
        agent: node.agent,
        label: node.id,
        layer,
      });

      maxWidth = Math.max(maxWidth, x + maidConfig.decisionRadius);
      maxHeight = Math.max(maxHeight, y + maidConfig.decisionRadius);
    }
  }

  // Step 4: Calculate edge positions
  for (const edge of game.edges) {
    const sourcePos = nodes.get(edge.source);
    const targetPos = nodes.get(edge.target);

    if (sourcePos && targetPos) {
      edges.push({
        sourceId: edge.source,
        targetId: edge.target,
        fromX: sourcePos.x,
        fromY: sourcePos.y,
        toX: targetPos.x,
        toY: targetPos.y,
      });
    }
  }

  return {
    nodes,
    edges,
    width: Math.max(maxWidth + 40, totalWidth),
    height: maxHeight + 60,
  };
}
