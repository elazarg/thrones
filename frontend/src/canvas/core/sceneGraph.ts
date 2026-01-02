import { Container, Application } from 'pixi.js';
import { Viewport } from 'pixi-viewport';
import { visualConfig } from '../config/visualConfig';

/** Standard layer names with z-ordering. */
export const LAYERS = {
  INFO_SETS: 'infoSets',       // z: 0 - Behind everything
  EDGES: 'edges',               // z: 10 - Connection lines
  NODES: 'nodes',               // z: 20 - Decision and outcome nodes
  LABELS: 'labels',             // z: 30 - Text labels
  OVERLAYS: 'overlays',         // z: 40 - Analysis overlays (equilibrium markers, etc.)
  INTERACTION: 'interaction',   // z: 50 - Interaction highlights (hover, selection)
} as const;

export type LayerName = typeof LAYERS[keyof typeof LAYERS];

/** Layer z-index values for consistent ordering. */
const LAYER_Z_INDEX: Record<LayerName, number> = {
  [LAYERS.INFO_SETS]: 0,
  [LAYERS.EDGES]: 10,
  [LAYERS.NODES]: 20,
  [LAYERS.LABELS]: 30,
  [LAYERS.OVERLAYS]: 40,
  [LAYERS.INTERACTION]: 50,
};

/**
 * SceneGraph manages the Pixi.js scene with named layers.
 * Provides a clean abstraction over Pixi.js container management.
 */
export class SceneGraph {
  private _viewport: Viewport;
  private _contentContainer: Container;
  private layers: Map<string, Container> = new Map();
  private elementContainers: Map<string, Container> = new Map();

  constructor(app: Application, worldWidth: number, worldHeight: number) {
    // Create viewport for zoom/pan
    this._viewport = new Viewport({
      screenWidth: app.screen.width,
      screenHeight: app.screen.height,
      worldWidth,
      worldHeight,
      events: app.renderer.events,
    });

    // Enable interactions
    const vpConfig = visualConfig.viewport;
    this._viewport
      .drag()
      .pinch({ percent: vpConfig.pinchPercent })
      .wheel({ percent: vpConfig.wheelPercent, smooth: vpConfig.wheelSmooth })
      .decelerate({ friction: vpConfig.decelerateFriction });

    app.stage.addChild(this._viewport);

    // Create content container with padding offset
    this._contentContainer = new Container();
    this._contentContainer.x = visualConfig.layout.padding;
    this._contentContainer.y = visualConfig.layout.padding;
    this._viewport.addChild(this._contentContainer);

    // Pre-create standard layers
    this.createStandardLayers();
  }

  /** Get the viewport for external control (fit, moveCenter, etc.). */
  get viewport(): Viewport {
    return this._viewport;
  }

  /** Get the content container (for direct access if needed). */
  get contentContainer(): Container {
    return this._contentContainer;
  }

  /** Create all standard layers with proper z-ordering. */
  private createStandardLayers(): void {
    // Create layers in z-order
    const layerOrder = Object.values(LAYERS).sort(
      (a, b) => LAYER_Z_INDEX[a] - LAYER_Z_INDEX[b]
    );

    for (const layerName of layerOrder) {
      const layer = new Container();
      layer.zIndex = LAYER_Z_INDEX[layerName];
      this._contentContainer.addChild(layer);
      this.layers.set(layerName, layer);
    }

    // Enable z-sorting on content container
    this._contentContainer.sortableChildren = true;
  }

  /** Get or create a layer by name. */
  getLayer(name: string, zIndex?: number): Container {
    let layer = this.layers.get(name);
    if (!layer) {
      layer = new Container();
      layer.zIndex = zIndex ?? 0;
      this._contentContainer.addChild(layer);
      this.layers.set(name, layer);
      this._contentContainer.sortChildren();
    }
    return layer;
  }

  /** Remove a layer by name. */
  removeLayer(name: string): void {
    const layer = this.layers.get(name);
    if (layer) {
      this._contentContainer.removeChild(layer);
      layer.destroy({ children: true });
      this.layers.delete(name);
    }
  }

  /** Clear all content from a specific layer. */
  clearLayer(name: string): void {
    const layer = this.layers.get(name);
    if (layer) {
      layer.removeChildren();
    }
  }

  /** Register an element container for later lookup. */
  registerElement(elementId: string, container: Container, layerName: string): void {
    this.elementContainers.set(elementId, container);
    const layer = this.getLayer(layerName);
    layer.addChild(container);
  }

  /** Get a registered element container by ID. */
  getElementContainer(elementId: string): Container | null {
    return this.elementContainers.get(elementId) ?? null;
  }

  /** Clear all element registrations. */
  clearElements(): void {
    this.elementContainers.clear();
  }

  /** Clear all content from all layers. */
  clear(): void {
    for (const layer of this.layers.values()) {
      layer.removeChildren();
    }
    this.elementContainers.clear();
  }

  /** Fit the viewport to show all content. */
  fitToView(contentWidth: number, contentHeight: number): void {
    const padding = visualConfig.layout.padding;
    const worldWidth = contentWidth + padding * 2;
    const worldHeight = contentHeight + padding * 2;

    this._viewport.fit(true, worldWidth, worldHeight);
    this._viewport.moveCenter(worldWidth / 2, worldHeight / 2);
  }

  /** Destroy the scene graph and clean up resources. */
  destroy(): void {
    this.clear();
    this.layers.clear();
    this._viewport.destroy();
  }
}
