import { BaseOverlayManager } from './BaseOverlayManager';
import type { MAIDOverlay, MAIDOverlayContext } from './types';
import { maidEquilibriumOverlay } from './MAIDEquilibriumOverlay';

/**
 * Overlay manager for MAID (Multi-Agent Influence Diagram) view.
 * Extends BaseOverlayManager with MAID-specific overlay registration.
 */
export class MAIDOverlayManager extends BaseOverlayManager<MAIDOverlay, MAIDOverlayContext> {
  constructor() {
    super();
    // Register default MAID overlays
    this.register(maidEquilibriumOverlay);
  }
}
