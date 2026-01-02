import { useRef, useCallback } from 'react';
import type { Container } from 'pixi.js';
import { OverlayManager, createDefaultOverlayManager } from '../overlays/OverlayManager';
import type { OverlayContext } from '../overlays/types';

/**
 * Hook for managing overlays on the canvas.
 * Creates an OverlayManager and provides methods to update/clear overlays.
 */
export function useOverlays() {
  const managerRef = useRef<OverlayManager | null>(null);

  // Lazy initialize the manager
  const getManager = useCallback(() => {
    if (!managerRef.current) {
      managerRef.current = createDefaultOverlayManager();
    }
    return managerRef.current;
  }, []);

  /**
   * Update overlays based on current context.
   */
  const updateOverlays = useCallback(
    (container: Container, context: OverlayContext) => {
      const manager = getManager();
      manager.update(container, context);
    },
    [getManager]
  );

  /**
   * Clear all overlays.
   */
  const clearOverlays = useCallback(
    (container: Container) => {
      const manager = getManager();
      manager.clear(container);
    },
    [getManager]
  );

  return {
    updateOverlays,
    clearOverlays,
    getManager,
  };
}
