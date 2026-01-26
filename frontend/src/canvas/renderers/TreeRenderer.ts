import { Container } from 'pixi.js';
import type { TreeLayout, NodePosition } from '../layout/treeLayout';
import type { VisualConfig } from '../config/visualConfig';
import type { ExtensiveFormGame } from '../../types';
import type { TreeRendererInterface, RenderContext } from './types';
import { renderDecisionNode } from './elements/DecisionNode';
import { renderOutcomeNode } from './elements/OutcomeNode';
import { renderEdge } from './elements/Edge';
import { renderInfoSetEnclosure } from './elements/InfoSetEnclosure';

/**
 * Group nodes by their information set.
 */
function groupByInfoSet(nodes: Map<string, NodePosition>): Map<string, NodePosition[]> {
  const groups = new Map<string, NodePosition[]>();
  for (const pos of nodes.values()) {
    if (pos.informationSet) {
      const existing = groups.get(pos.informationSet) || [];
      existing.push(pos);
      groups.set(pos.informationSet, existing);
    }
  }
  return groups;
}

/**
 * TreeRenderer renders game trees using the element renderers.
 * It handles the base visualization without analysis overlays.
 */
export class TreeRenderer implements TreeRendererInterface {
  /**
   * Render the entire tree to the given container.
   */
  render(
    container: Container,
    _game: ExtensiveFormGame,
    layout: TreeLayout,
    context: RenderContext
  ): void {
    const { config, players, onNodeHover } = context;

    // 1. Draw information set enclosures first (behind everything)
    this.renderInfoSets(container, layout, config);

    // 2. Draw edges
    this.renderEdges(container, layout, config);

    // 3. Draw nodes (on top)
    this.renderNodes(container, layout, players, config, onNodeHover);
  }

  /**
   * Render information set enclosures.
   */
  private renderInfoSets(
    container: Container,
    layout: TreeLayout,
    config: VisualConfig
  ): void {
    const infoSetGroups = groupByInfoSet(layout.nodes);
    const allInfoSets = Array.from(infoSetGroups.keys());

    for (const [infoSetId, nodesInSet] of infoSetGroups) {
      if (nodesInSet.length > 1) {
        renderInfoSetEnclosure(container, infoSetId, nodesInSet, allInfoSets, config);
      }
    }
  }

  /**
   * Render all edges.
   */
  private renderEdges(
    container: Container,
    layout: TreeLayout,
    config: VisualConfig
  ): void {
    for (const edge of layout.edges) {
      renderEdge(container, edge, config);
    }
  }

  /**
   * Render all nodes.
   */
  private renderNodes(
    container: Container,
    layout: TreeLayout,
    players: string[],
    config: VisualConfig,
    onNodeHover?: (nodeId: string | null) => void
  ): void {
    for (const [nodeId, pos] of layout.nodes) {
      if (pos.type === 'decision') {
        renderDecisionNode(container, nodeId, pos, players, config, onNodeHover);
      } else {
        renderOutcomeNode(container, nodeId, pos, config, onNodeHover);
      }
    }
  }

  /**
   * Clear all rendered content from the container.
   */
  clear(container: Container): void {
    container.removeChildren();
  }
}

// Singleton instance for convenience
export const treeRenderer = new TreeRenderer();
