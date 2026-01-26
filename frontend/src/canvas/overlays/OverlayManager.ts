import type { Overlay, OverlayContext } from './types';
import { BaseOverlayManager } from './BaseOverlayManager';

/**
 * OverlayManager coordinates multiple overlays on the tree scene.
 */
export class OverlayManager extends BaseOverlayManager<Overlay, OverlayContext> {}

// Default manager with standard overlays
import { equilibriumOverlay } from './EquilibriumOverlay';
import { edgeProbabilityOverlay } from './EdgeProbabilityOverlay';

export function createDefaultOverlayManager(): OverlayManager {
  const manager = new OverlayManager();
  manager.register(edgeProbabilityOverlay); // Lower z-index, renders first
  manager.register(equilibriumOverlay);
  return manager;
}
