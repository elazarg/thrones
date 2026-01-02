import { Container, Text, TextStyle } from 'pixi.js';
import type { Overlay, OverlayContext } from './types';
import { isMatchingPayoffs } from './types';
import type { VisualConfig } from '../config/visualConfig';

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
 */
export class EquilibriumOverlay implements Overlay {
  id = 'equilibrium';
  zIndex = 100;

  private overlayContainer: Container | null = null;

  compute(context: OverlayContext): EquilibriumOverlayData | null {
    const { selectedEquilibrium, layout, config } = context;

    if (!selectedEquilibrium) {
      return null;
    }

    const equilibriumNodes: EquilibriumOverlayData['equilibriumNodes'] = [];

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

    // Create overlay container
    this.overlayContainer = new Container();
    this.overlayContainer.zIndex = this.zIndex;

    const { text: textConfig, equilibrium: eqConfig } = config;

    for (const node of overlayData.equilibriumNodes) {
      const starStyle = new TextStyle({
        fontFamily: textConfig.fontFamily,
        fontSize: eqConfig.starSize,
        fill: eqConfig.starColor,
      });
      const star = new Text({ text: '\u2605', style: starStyle });
      star.anchor.set(0.5, 1);
      star.x = node.x;
      star.y = node.y - node.nodeSize - 4;
      this.overlayContainer.addChild(star);
    }

    container.addChild(this.overlayContainer);
  }

  clear(container: Container): void {
    if (this.overlayContainer) {
      container.removeChild(this.overlayContainer);
      this.overlayContainer.destroy({ children: true });
      this.overlayContainer = null;
    }
  }
}

// Singleton instance
export const equilibriumOverlay = new EquilibriumOverlay();
