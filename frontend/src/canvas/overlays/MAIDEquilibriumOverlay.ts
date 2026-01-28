import { Container, Graphics } from 'pixi.js';
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
  }>;
}

/**
 * Overlay that highlights equilibrium decision nodes with a gold ring.
 */
export class MAIDEquilibriumOverlay implements MAIDOverlay {
  id = 'maid-equilibrium';
  zIndex = 100;

  compute(context: MAIDOverlayContext): MAIDEquilibriumOverlayData | null {
    const { selectedEquilibrium, layout, config } = context;

    if (!selectedEquilibrium) {
      return null;
    }

    // Highlight all decision nodes when an equilibrium is selected
    // In a MAID, the equilibrium strategies apply to decision nodes
    const highlightNodes: MAIDEquilibriumOverlayData['highlightNodes'] = [];

    for (const pos of layout.nodes.values()) {
      if (pos.type === 'decision') {
        highlightNodes.push({
          x: pos.x,
          y: pos.y,
          radius: config.maid.decisionRadius,
        });
      }
    }

    return highlightNodes.length > 0 ? { highlightNodes } : null;
  }

  apply(container: Container, data: unknown, config: VisualConfig): void {
    const overlayData = data as MAIDEquilibriumOverlayData;

    // Create overlay container with label for identification
    const overlayContainer = new Container();
    overlayContainer.label = OVERLAY_LABEL;
    overlayContainer.zIndex = this.zIndex;

    const { equilibrium: eqConfig } = config;

    for (const node of overlayData.highlightNodes) {
      const graphics = new Graphics();

      // Draw gold ring around decision node
      graphics
        .circle(node.x, node.y, node.radius + 4)
        .stroke({
          width: eqConfig.borderWidth,
          color: eqConfig.borderColor,
          alpha: 0.8,
        });

      overlayContainer.addChild(graphics);
    }

    container.addChild(overlayContainer);
  }

  clear(container: Container): void {
    const overlayContainer = container.children.find(
      (child) => child.label === OVERLAY_LABEL
    );
    if (overlayContainer) {
      container.removeChild(overlayContainer);
      overlayContainer.destroy({ children: true });
    }
  }
}

// Singleton instance
export const maidEquilibriumOverlay = new MAIDEquilibriumOverlay();
