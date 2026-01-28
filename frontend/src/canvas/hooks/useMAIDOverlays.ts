import { useRef, useCallback } from 'react';
import type { Container } from 'pixi.js';
import { maidEquilibriumOverlay, type MAIDOverlayContext, type MAIDOverlay } from '../overlays/MAIDEquilibriumOverlay';
import { visualConfig } from '../config/visualConfig';

/**
 * Manager for MAID overlays.
 */
class MAIDOverlayManager {
  private overlays: MAIDOverlay[] = [];

  constructor() {
    this.overlays = [maidEquilibriumOverlay];
  }

  /**
   * Update all overlays based on context.
   */
  update(container: Container, context: MAIDOverlayContext): void {
    // Clear and reapply all overlays
    for (const overlay of this.overlays) {
      overlay.clear(container);
      const data = overlay.compute(context);
      if (data) {
        overlay.apply(container, data, visualConfig);
      }
    }
  }

  /**
   * Clear all overlays.
   */
  clear(container: Container): void {
    for (const overlay of this.overlays) {
      overlay.clear(container);
    }
  }
}

/**
 * Hook for managing MAID overlays on the canvas.
 */
export function useMAIDOverlays() {
  const managerRef = useRef<MAIDOverlayManager | null>(null);

  const getManager = useCallback(() => {
    if (!managerRef.current) {
      managerRef.current = new MAIDOverlayManager();
    }
    return managerRef.current;
  }, []);

  /**
   * Update overlays based on current context.
   */
  const updateMAIDOverlays = useCallback(
    (container: Container, context: MAIDOverlayContext) => {
      const manager = getManager();
      manager.update(container, context);
    },
    [getManager]
  );

  /**
   * Clear all overlays.
   */
  const clearMAIDOverlays = useCallback(
    (container: Container) => {
      const manager = getManager();
      manager.clear(container);
    },
    [getManager]
  );

  return {
    updateMAIDOverlays,
    clearMAIDOverlays,
    getManager,
  };
}
