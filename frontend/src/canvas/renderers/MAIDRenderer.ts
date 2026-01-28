import { Container } from 'pixi.js';
import type { MAIDLayout } from '../layout/maidLayout';
import type { VisualConfig } from '../config/visualConfig';
import type { MAIDGame } from '../../types';
import { renderMAIDDecisionNode } from './elements/MAIDDecisionNode';
import { renderMAIDUtilityNode } from './elements/MAIDUtilityNode';
import { renderMAIDChanceNode } from './elements/MAIDChanceNode';
import { renderMAIDEdge } from './elements/MAIDEdge';

export interface MAIDRenderContext {
  config: VisualConfig;
  agents: string[];
  onNodeHover?: (nodeId: string | null) => void;
}

/**
 * MAIDRenderer renders Multi-Agent Influence Diagrams.
 */
export class MAIDRenderer {
  /**
   * Render the entire MAID to the given container.
   */
  render(
    container: Container,
    _game: MAIDGame,
    layout: MAIDLayout,
    context: MAIDRenderContext
  ): void {
    const { config, agents, onNodeHover } = context;

    // 1. Draw edges first (behind nodes)
    this.renderEdges(container, layout, config);

    // 2. Draw nodes (on top)
    this.renderNodes(container, layout, agents, config, onNodeHover);
  }

  /**
   * Render all edges.
   */
  private renderEdges(
    container: Container,
    layout: MAIDLayout,
    config: VisualConfig
  ): void {
    for (const edge of layout.edges) {
      const sourceNode = layout.nodes.get(edge.sourceId);
      const targetNode = layout.nodes.get(edge.targetId);

      if (sourceNode && targetNode) {
        renderMAIDEdge(container, edge, sourceNode, targetNode, config);
      }
    }
  }

  /**
   * Render all nodes.
   */
  private renderNodes(
    container: Container,
    layout: MAIDLayout,
    agents: string[],
    config: VisualConfig,
    onNodeHover?: (nodeId: string | null) => void
  ): void {
    for (const pos of layout.nodes.values()) {
      switch (pos.type) {
        case 'decision':
          renderMAIDDecisionNode(container, pos, agents, config, onNodeHover);
          break;
        case 'utility':
          renderMAIDUtilityNode(container, pos, agents, config, onNodeHover);
          break;
        case 'chance':
          renderMAIDChanceNode(container, pos, config, onNodeHover);
          break;
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
export const maidRenderer = new MAIDRenderer();
