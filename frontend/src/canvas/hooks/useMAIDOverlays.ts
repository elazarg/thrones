import { useRef, useCallback } from 'react';
import type { Container } from 'pixi.js';
import type { MAIDOverlayContext } from '../overlays/types';
import { MAIDOverlayManager } from '../overlays/MAIDOverlayManager';

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
