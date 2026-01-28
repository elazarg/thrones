import { Container, TextStyle } from 'pixi.js';
import { createText } from '../utils/textUtils';
import { clearOverlayByLabel } from './overlayUtils';
import type { Overlay, OverlayContext } from './types';
import { isMatchingPayoffs } from './types';
import type { VisualConfig } from '../config/visualConfig';

/** Unique label for equilibrium overlay container */
const OVERLAY_LABEL = '__equilibrium_overlay__';

/**
 * Check if an equilibrium is pure (all probabilities are 0 or 1).
 */
function isPureEquilibrium(behaviorProfile: Record<string, Record<string, number>>): boolean {
  for (const strategies of Object.values(behaviorProfile)) {
    for (const prob of Object.values(strategies)) {
      if (prob > 0.001 && prob < 0.999) {
        return false; // Mixed strategy
      }
    }
  }
  return true;
}

/**
 * Data for equilibrium overlay - positions where stars should be drawn.
 */
interface EquilibriumOverlayData {
  equilibriumNodes: Array<{
    x: number;
    y: number;
    nodeSize: number;
  }>;
}

/**
 * Overlay that highlights equilibrium outcomes with star markers.
 * Stars are only shown for pure strategy equilibria.
 * For mixed equilibria, edge probabilities convey the information instead.
 */
export class EquilibriumOverlay implements Overlay {
  id = 'equilibrium';
  zIndex = 100;

  compute(context: OverlayContext): EquilibriumOverlayData | null {
    const { selectedEquilibrium, layout, config } = context;

    if (!selectedEquilibrium) {
      return null;
    }

    // Only show stars for pure equilibria
    // Mixed equilibria are shown via edge probabilities instead
    if (!isPureEquilibrium(selectedEquilibrium.behavior_profile)) {
      return null;
    }

    const equilibriumNodes: EquilibriumOverlayData['equilibriumNodes'] = [];

    // Skip if no payoffs in equilibrium (e.g., MAID equilibria)
    if (!selectedEquilibrium.payoffs) {
      return null;
    }

    for (const pos of layout.nodes.values()) {
      if (pos.type === 'outcome' && pos.payoffs) {
        if (isMatchingPayoffs(pos.payoffs, selectedEquilibrium.payoffs)) {
          equilibriumNodes.push({
            x: pos.x,
            y: pos.y,
            nodeSize: config.node.outcomeSize,
          });
        }
      }
    }

    return equilibriumNodes.length > 0 ? { equilibriumNodes } : null;
  }

  apply(container: Container, data: unknown, config: VisualConfig): void {
    const overlayData = data as EquilibriumOverlayData;

    // Create overlay container with label for identification
    const overlayContainer = new Container();
    overlayContainer.label = OVERLAY_LABEL;
    overlayContainer.zIndex = this.zIndex;

    const { text: textConfig, equilibrium: eqConfig } = config;

    for (const node of overlayData.equilibriumNodes) {
      const starStyle = new TextStyle({
        fontFamily: textConfig.fontFamily,
        fontSize: eqConfig.starSize,
        fill: eqConfig.starColor,
      });
      const star = createText({ text: '\u2605', style: starStyle });
      star.anchor.set(0.5, 1);
      star.x = node.x;
      star.y = node.y - node.nodeSize - 4;
      overlayContainer.addChild(star);
    }

    container.addChild(overlayContainer);
  }

  clear(container: Container): void {
    clearOverlayByLabel(container, OVERLAY_LABEL);
  }
}

// Singleton instance
export const equilibriumOverlay = new EquilibriumOverlay();
