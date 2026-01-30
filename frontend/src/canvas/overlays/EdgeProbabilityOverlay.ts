import { Container, Graphics, TextStyle } from 'pixi.js';
import { createText } from '../utils/textUtils';
import { clearOverlayByLabel } from './overlayUtils';
import { PROBABILITY_EPSILON, PURE_STRATEGY_THRESHOLD } from './types';
import type { Overlay, OverlayContext } from './types';
import type { VisualConfig } from '../config/visualConfig';

/** Unique label for edge probability overlay container */
const OVERLAY_LABEL = '__edge_probability_overlay__';

/**
 * Format probability as a nice fraction or percentage.
 * Common fractions (1/2, 1/3, 2/3, 1/4, 3/4) are shown as fractions.
 */
function formatProbability(p: number): string {
  const tolerance = PROBABILITY_EPSILON;

  // Common fractions
  const fractions: [number, string][] = [
    [1 / 2, '½'],
    [1 / 3, '⅓'],
    [2 / 3, '⅔'],
    [1 / 4, '¼'],
    [3 / 4, '¾'],
    [1 / 5, '⅕'],
    [2 / 5, '⅖'],
    [3 / 5, '⅗'],
    [4 / 5, '⅘'],
    [1 / 6, '⅙'],
    [5 / 6, '⅚'],
  ];

  for (const [value, symbol] of fractions) {
    if (Math.abs(p - value) < tolerance) {
      return symbol;
    }
  }

  // Otherwise show percentage
  return `${Math.round(p * 100)}%`;
}

/**
 * Data for edge probability overlay.
 */
interface EdgeProbabilityData {
  edges: Array<{
    fromX: number;
    fromY: number;
    toX: number;
    toY: number;
    probability: number;
    label: string;
  }>;
}

/**
 * Overlay that shows action probabilities on edges.
 * For pure strategies, edges have probability 0 or 1.
 * For mixed strategies, edges show the probability of that action being played.
 */
export class EdgeProbabilityOverlay implements Overlay {
  id = 'edge-probability';
  zIndex = 90; // Below equilibrium stars but above base edges

  compute(context: OverlayContext): EdgeProbabilityData | null {
    const { selectedEquilibrium, layout, game } = context;

    if (!selectedEquilibrium) {
      return null;
    }

    const edges: EdgeProbabilityData['edges'] = [];
    const { behavior_profile } = selectedEquilibrium;

    // Build a map of (nodeId, action) -> probability
    const nodeActionProbabilities = new Map<string, number>();

    // Check if this is a MAID equilibrium (keyed by decision node ID like "D1")
    // vs Gambit equilibrium (keyed by player name with strategy labels)
    const firstKey = Object.keys(behavior_profile)[0];
    const isMAIDFormat = firstKey && game.nodes[firstKey] !== undefined;

    // Check if viewing a converted EFG with MAID node mapping
    const maidToEfgNodes = (game as { maid_to_efg_nodes?: Record<string, string[]> }).maid_to_efg_nodes;
    const isMAIDEquilibriumOnConvertedEFG = !isMAIDFormat && maidToEfgNodes && firstKey && maidToEfgNodes[firstKey] !== undefined;

    if (isMAIDFormat) {
      // MAID format: behavior_profile is { nodeId: { action: prob } }
      // The node IDs directly match game.nodes
      for (const [nodeId, actions] of Object.entries(behavior_profile)) {
        for (const [action, prob] of Object.entries(actions as Record<string, number>)) {
          if (prob > PROBABILITY_EPSILON) {
            const key = `${nodeId}:${action}`;
            nodeActionProbabilities.set(key, prob);
          }
        }
      }
    } else if (isMAIDEquilibriumOnConvertedEFG) {
      // MAID equilibrium viewed on converted EFG
      // Use the maid_to_efg_nodes mapping to translate node IDs
      for (const [maidNodeId, actions] of Object.entries(behavior_profile)) {
        const efgNodeIds = maidToEfgNodes[maidNodeId];
        if (!efgNodeIds) continue;

        for (const [action, prob] of Object.entries(actions as Record<string, number>)) {
          if (prob > PROBABILITY_EPSILON) {
            // Map the action probability to all corresponding EFG nodes
            for (const efgNodeId of efgNodeIds) {
              const key = `${efgNodeId}:${action}`;
              nodeActionProbabilities.set(key, prob);
            }
          }
        }
      }
    } else {
      // Gambit format: behavior_profile is { player: { strategyLabel: prob } }
      // Strategy labels are ordered by sorted node IDs (matching backend)
      for (const [player, strategies] of Object.entries(behavior_profile)) {
        // Get this player's decision nodes, sorted by ID (same order as backend)
        const playerNodes = Object.entries(game.nodes)
          .filter(([, node]) => node.player === player)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([id]) => id);

        for (const [strategyLabel, prob] of Object.entries(strategies)) {
          // Split strategy into actions (one per node in sorted order)
          const actions = strategyLabel.split('/');

          // Map each action to its specific node
          for (let i = 0; i < Math.min(actions.length, playerNodes.length); i++) {
            const nodeId = playerNodes[i];
            const action = actions[i];
            const key = `${nodeId}:${action}`;
            // Accumulate probability for this (node, action) pair
            nodeActionProbabilities.set(key, (nodeActionProbabilities.get(key) || 0) + prob);
          }
        }
      }
    }

    // Map edges to probabilities
    for (const edge of layout.edges) {
      const key = `${edge.fromId}:${edge.label}`;
      const probability = nodeActionProbabilities.get(key);

      // Only include edges where we found a probability
      if (probability !== undefined && probability > PROBABILITY_EPSILON) {
        edges.push({
          fromX: edge.fromX,
          fromY: edge.fromY,
          toX: edge.toX,
          toY: edge.toY,
          probability,
          label: edge.label,
        });
      }
    }

    return edges.length > 0 ? { edges } : null;
  }

  apply(container: Container, data: unknown, config: VisualConfig): void {
    const overlayData = data as EdgeProbabilityData;

    const overlayContainer = new Container();
    overlayContainer.label = OVERLAY_LABEL;
    overlayContainer.zIndex = this.zIndex;

    const { node: nodeConfig, edge: edgeConfig } = config;

    for (const edge of overlayData.edges) {
      // Draw highlight line - thickness proportional to probability
      const graphics = new Graphics();

      // Thickness: 2px base + up to 4px more based on probability
      const thickness = 2 + edge.probability * 4;
      // Alpha: higher for higher probability
      const alpha = 0.2 + edge.probability * 0.5;

      graphics
        .moveTo(edge.fromX, edge.fromY + nodeConfig.decisionRadius)
        .lineTo(edge.toX, edge.toY - nodeConfig.decisionRadius)
        .stroke({
          width: thickness,
          color: 0x58a6ff, // Blue highlight
          alpha,
        });

      overlayContainer.addChild(graphics);

      // Add probability label for non-trivial probabilities (not 0 or 1)
      // Positioned at edge midpoint (action labels are near target nodes)
      if (edge.probability > PROBABILITY_EPSILON && edge.probability < PURE_STRATEGY_THRESHOLD) {
        const midX = (edge.fromX + edge.toX) / 2;
        const midY = (edge.fromY + edge.toY) / 2;

        const probStyle = new TextStyle({
          fontFamily: config.text.fontFamily,
          fontSize: 11,
          fill: 0x58a6ff,
          fontWeight: 'bold',
        });

        const probText = createText({
          text: formatProbability(edge.probability),
          style: probStyle,
        });
        probText.anchor.set(0.5, 0.5);
        probText.x = midX + edgeConfig.labelOffset;
        probText.y = midY;

        overlayContainer.addChild(probText);
      }
    }

    container.addChild(overlayContainer);
  }

  clear(container: Container): void {
    clearOverlayByLabel(container, OVERLAY_LABEL);
  }
}

export const edgeProbabilityOverlay = new EdgeProbabilityOverlay();
