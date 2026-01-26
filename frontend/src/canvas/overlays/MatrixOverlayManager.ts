import type { MatrixOverlay, MatrixOverlayContext } from './types';
import { BaseOverlayManager } from './BaseOverlayManager';
import { matrixEquilibriumOverlay } from './MatrixEquilibriumOverlay';
import { matrixIESDSOverlay } from './MatrixIESDSOverlay';

/**
 * MatrixOverlayManager coordinates overlays for matrix views.
 */
export class MatrixOverlayManager extends BaseOverlayManager<
  MatrixOverlay,
  MatrixOverlayContext
> {}

/**
 * Create a matrix overlay manager with default overlays.
 */
export function createDefaultMatrixOverlayManager(): MatrixOverlayManager {
  const manager = new MatrixOverlayManager();
  manager.register(matrixEquilibriumOverlay);
  manager.register(matrixIESDSOverlay);
  return manager;
}
