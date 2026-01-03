import { useRef, useCallback } from 'react';
import type { Container } from 'pixi.js';
import {
  MatrixOverlayManager,
  createDefaultMatrixOverlayManager,
} from '../overlays/MatrixOverlayManager';
import type { MatrixOverlayContext } from '../overlays/types';

/**
 * Hook for managing matrix overlays on the canvas.
 */
export function useMatrixOverlays() {
  const managerRef = useRef<MatrixOverlayManager | null>(null);

  // Lazy initialize the manager
  const getManager = useCallback(() => {
    if (!managerRef.current) {
      managerRef.current = createDefaultMatrixOverlayManager();
    }
    return managerRef.current;
  }, []);

  /**
   * Update overlays based on current context.
   */
  const updateMatrixOverlays = useCallback(
    (container: Container, context: MatrixOverlayContext) => {
      const manager = getManager();
      manager.update(container, context);
    },
    [getManager]
  );

  /**
   * Clear all overlays.
   */
  const clearMatrixOverlays = useCallback(
    (container: Container) => {
      const manager = getManager();
      manager.clear(container);
    },
    [getManager]
  );

  return {
    updateMatrixOverlays,
    clearMatrixOverlays,
    getManager,
  };
}
