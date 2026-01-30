import { Container, Graphics, TextStyle } from 'pixi.js';
import { createText } from '../utils/textUtils';
import { clearOverlayByLabel } from './overlayUtils';
import { PURE_STRATEGY_THRESHOLD } from './types';
import type { MAIDOverlay, MAIDOverlayContext } from './types';
import type { VisualConfig } from '../config/visualConfig';
import type { MAIDGame, NashEquilibrium } from '../../types';

/** Unique label for MAID equilibrium overlay container */
const OVERLAY_LABEL = '__maid_equilibrium_overlay__';

/**
 * Data for MAID equilibrium overlay.
 */
interface MAIDEquilibriumOverlayData {
  highlightNodes: Array<{
    x: number;
    y: number;
    radius: number;
    action?: string;
    probability?: number;
  }>;
}

/**
 * Normalize Gambit equilibrium (keyed by player/agent) to MAID format (keyed by decision node ID).
 * For simple MAIDs with 1 decision per agent, strategy labels map directly to actions.
 * For complex MAIDs with multiple decisions per agent, compound strategies need splitting.
 */
function normalizeGambitToMAID(
  equilibrium: NashEquilibrium,
  game: MAIDGame
): Record<string, Record<string, number>> | null {
  const profile = equilibrium.behavior_profile || equilibrium.strategies;
  if (!profile) return null;

  // Check if already in MAID format (keys are decision node IDs)
  const decisionNodeIds = new Set(
    game.nodes.filter(n => n.type === 'decision').map(n => n.id)
  );
  const firstKey = Object.keys(profile)[0];
  if (firstKey && decisionNodeIds.has(firstKey)) {
    // Already in MAID format
    return profile as Record<string, Record<string, number>>;
  }

  // Build agent -> decision nodes mapping from MAID
  const agentDecisions: Record<string, string[]> = {};
  for (const node of game.nodes) {
    if (node.type === 'decision' && node.agent) {
      if (!agentDecisions[node.agent]) {
        agentDecisions[node.agent] = [];
      }
      agentDecisions[node.agent].push(node.id);
    }
  }

  // Convert Gambit format to MAID format
  const result: Record<string, Record<string, number>> = {};

  for (const [agent, strategies] of Object.entries(profile)) {
    const decisionNodes = agentDecisions[agent];
    if (!decisionNodes || decisionNodes.length === 0) continue;

    for (const [strategyLabel, prob] of Object.entries(strategies as Record<string, number>)) {
      // Split compound strategy label (e.g., "C/D" -> ["C", "D"])
      const actions = strategyLabel.split('/');

      // Map each action to its decision node (in sorted order, matching EFG conversion)
      const sortedNodes = [...decisionNodes].sort();
      for (let i = 0; i < Math.min(actions.length, sortedNodes.length); i++) {
        const nodeId = sortedNodes[i];
        const action = actions[i];

        if (!result[nodeId]) {
          result[nodeId] = {};
        }
        result[nodeId][action] = (result[nodeId][action] ?? 0) + prob;
      }

      // For single-decision agents with simple strategy labels
      if (actions.length === 1 && sortedNodes.length === 1) {
        const nodeId = sortedNodes[0];
        if (!result[nodeId]) {
          result[nodeId] = {};
        }
        result[nodeId][actions[0]] = (result[nodeId][actions[0]] ?? 0) + prob;
      }
    }
  }

  return Object.keys(result).length > 0 ? result : null;
}

/**
 * Get the chosen action for a decision node from the equilibrium.
 * Handles both MAID equilibria (keyed by decision node ID) and
 * Gambit equilibria (keyed by player/agent name).
 */
function getChosenAction(
  profile: Record<string, Record<string, number>>,
  nodeId: string
): { action: string; probability: number } | null {
  const nodeStrategy = profile[nodeId];
  if (!nodeStrategy) return null;

  // Find the action with highest probability
  let bestAction: string | null = null;
  let bestProb = 0;

  for (const [action, prob] of Object.entries(nodeStrategy)) {
    if (prob > bestProb) {
      bestProb = prob;
      bestAction = action;
    }
  }

  return bestAction ? { action: bestAction, probability: bestProb } : null;
}

/**
 * Overlay that highlights equilibrium decision nodes with a gold ring
 * and shows the chosen action.
 */
export class MAIDEquilibriumOverlay implements MAIDOverlay {
  id = 'maid-equilibrium';
  zIndex = 100;

  compute(context: MAIDOverlayContext): MAIDEquilibriumOverlayData | null {
    const { selectedEquilibrium, layout, config, game } = context;

    if (!selectedEquilibrium) {
      return null;
    }

    // Normalize equilibrium to MAID format (handles both MAID and Gambit equilibria)
    const normalizedProfile = normalizeGambitToMAID(selectedEquilibrium, game);
    if (!normalizedProfile) {
      return null;
    }

    const highlightNodes: MAIDEquilibriumOverlayData['highlightNodes'] = [];

    for (const pos of layout.nodes.values()) {
      if (pos.type === 'decision') {
        const chosen = getChosenAction(normalizedProfile, pos.id);
        highlightNodes.push({
          x: pos.x,
          y: pos.y,
          radius: config.maid.decisionRadius,
          action: chosen?.action,
          probability: chosen?.probability,
        });
      }
    }

    return highlightNodes.length > 0 ? { highlightNodes } : null;
  }

  apply(container: Container, data: unknown, config: VisualConfig): void {
    const overlayData = data as MAIDEquilibriumOverlayData;

    const overlayContainer = new Container();
    overlayContainer.label = OVERLAY_LABEL;
    overlayContainer.zIndex = this.zIndex;

    const { equilibrium: eqConfig, text: textConfig } = config;

    for (const node of overlayData.highlightNodes) {
      const graphics = new Graphics();

      // Draw gold ring around decision node
      graphics
        .circle(node.x, node.y, node.radius + 6)
        .stroke({
          width: eqConfig.borderWidth + 1,
          color: eqConfig.borderColor,
          alpha: 0.9,
        });

      overlayContainer.addChild(graphics);

      // Show the chosen action below the node
      if (node.action) {
        const actionStyle = new TextStyle({
          fontFamily: textConfig.fontFamily,
          fontSize: 12,
          fill: eqConfig.borderColor,
          fontWeight: 'bold',
        });

        const label = node.probability && node.probability < PURE_STRATEGY_THRESHOLD
          ? `${node.action} (${Math.round(node.probability * 100)}%)`
          : node.action;

        const actionText = createText({
          text: label,
          style: actionStyle,
        });
        actionText.anchor.set(0.5, 0);
        actionText.x = node.x;
        actionText.y = node.y + node.radius + 10;

        overlayContainer.addChild(actionText);
      }
    }

    container.addChild(overlayContainer);
  }

  clear(container: Container): void {
    clearOverlayByLabel(container, OVERLAY_LABEL);
  }
}

// Singleton instance
export const maidEquilibriumOverlay = new MAIDEquilibriumOverlay();
