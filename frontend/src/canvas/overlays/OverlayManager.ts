import type { Container } from 'pixi.js';
import type { Overlay, OverlayContext } from './types';
import type { VisualConfig } from '../config/visualConfig';

/**
 * OverlayManager coordinates multiple overlays on the scene.
 * It handles computing, applying, and clearing overlays in z-order.
 */
export class OverlayManager {
  private overlays: Overlay[] = [];
  private overlayData: Map<string, unknown> = new Map();

  /**
   * Register an overlay with the manager.
   */
  register(overlay: Overlay): void {
    this.overlays.push(overlay);
    // Keep sorted by z-index
    this.overlays.sort((a, b) => a.zIndex - b.zIndex);
  }

  /**
   * Unregister an overlay.
   */
  unregister(overlayId: string): void {
    const index = this.overlays.findIndex((o) => o.id === overlayId);
    if (index !== -1) {
      this.overlays.splice(index, 1);
      this.overlayData.delete(overlayId);
    }
  }

  /**
   * Compute all overlays based on context.
   */
  compute(context: OverlayContext): void {
    this.overlayData.clear();
    for (const overlay of this.overlays) {
      const data = overlay.compute(context);
      if (data !== null) {
        this.overlayData.set(overlay.id, data);
      }
    }
  }

  /**
   * Apply all computed overlays to the container.
   */
  apply(container: Container, config: VisualConfig): void {
    for (const overlay of this.overlays) {
      const data = this.overlayData.get(overlay.id);
      if (data !== undefined) {
        overlay.apply(container, data, config);
      }
    }
  }

  /**
   * Clear all overlays from the container.
   */
  clear(container: Container): void {
    for (const overlay of this.overlays) {
      overlay.clear(container);
    }
    this.overlayData.clear();
  }

  /**
   * Compute and apply overlays in one call.
   */
  update(container: Container, context: OverlayContext): void {
    this.clear(container);
    this.compute(context);
    this.apply(container, context.config);
  }

  /**
   * Get registered overlay IDs.
   */
  getOverlayIds(): string[] {
    return this.overlays.map((o) => o.id);
  }
}

// Default manager with standard overlays
import { equilibriumOverlay } from './EquilibriumOverlay';
import { edgeProbabilityOverlay } from './EdgeProbabilityOverlay';

export function createDefaultOverlayManager(): OverlayManager {
  const manager = new OverlayManager();
  manager.register(edgeProbabilityOverlay); // Lower z-index, renders first
  manager.register(equilibriumOverlay);
  return manager;
}
