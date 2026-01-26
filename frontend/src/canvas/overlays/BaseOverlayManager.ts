import type { Container } from 'pixi.js';
import type { VisualConfig } from '../config/visualConfig';

/**
 * Base interface for overlays with different context types.
 */
export interface BaseOverlay<TContext> {
  id: string;
  zIndex: number;
  compute(context: TContext): unknown | null;
  apply(container: Container, data: unknown, config: VisualConfig): void;
  clear(container: Container): void;
}

/**
 * Base context interface that all overlay contexts share.
 */
export interface BaseOverlayContext {
  config: VisualConfig;
}

/**
 * Generic overlay manager that coordinates multiple overlays.
 * Parameterized by overlay type and context type.
 */
export class BaseOverlayManager<
  TOverlay extends BaseOverlay<TContext>,
  TContext extends BaseOverlayContext,
> {
  protected overlays: TOverlay[] = [];
  protected overlayData: Map<string, unknown> = new Map();

  /**
   * Register an overlay with the manager.
   */
  register(overlay: TOverlay): void {
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
  compute(context: TContext): void {
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
  update(container: Container, context: TContext): void {
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
