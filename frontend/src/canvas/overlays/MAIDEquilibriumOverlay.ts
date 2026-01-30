import { Container, Graphics, TextStyle } from 'pixi.js';
import { createText } from '../utils/textUtils';
import { clearOverlayByLabel } from './overlayUtils';
import type { VisualConfig } from '../config/visualConfig';
import type { MAIDLayout } from '../layout/maidLayout';
import type { MAIDGame, NashEquilibrium, AnalysisResult, IESDSResult } from '../../types';

/** Unique label for MAID equilibrium overlay container */
const OVERLAY_LABEL = '__maid_equilibrium_overlay__';

/**
 * Context for MAID overlays.
 */
export interface MAIDOverlayContext {
  game: MAIDGame;
  layout: MAIDLayout;
  config: VisualConfig;
  agents: string[];
  analysisResults: AnalysisResult[];
  selectedEquilibrium: NashEquilibrium | null;
  selectedIESDSResult: IESDSResult | null;
}

/**
 * Interface for MAID overlays.
 */
export interface MAIDOverlay {
  id: string;
  zIndex: number;
  compute(context: MAIDOverlayContext): unknown | null;
  apply(container: Container, data: unknown, config: VisualConfig): void;
  clear(container: Container): void;
}

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
 * Get the chosen action for a decision node from the equilibrium.
 * MAID equilibria have behavior_profile keyed by decision node ID.
 */
function getChosenAction(
  equilibrium: NashEquilibrium,
  nodeId: string
): { action: string; probability: number } | null {
  const profile = equilibrium.behavior_profile || equilibrium.strategies;
  if (!profile) return null;

  // MAID equilibria: behavior_profile is keyed by decision node ID
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
    const { selectedEquilibrium, layout, config } = context;

    if (!selectedEquilibrium) {
      return null;
    }

    const highlightNodes: MAIDEquilibriumOverlayData['highlightNodes'] = [];

    for (const pos of layout.nodes.values()) {
      if (pos.type === 'decision') {
        const chosen = getChosenAction(selectedEquilibrium, pos.id);
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

        const label = node.probability && node.probability < 0.999
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
