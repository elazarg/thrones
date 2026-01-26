import type { Container } from 'pixi.js';
import type { VisualConfig } from '../config/visualConfig';
import type { TreeLayout } from '../layout/treeLayout';
import type { ExtensiveFormGame } from '../../types';

/**
 * Context passed to renderers.
 */
export interface RenderContext {
  config: VisualConfig;
  players: string[];
  onNodeHover?: (nodeId: string | null) => void;
}

/**
 * Renderer interface for tree-based visualizations.
 */
export interface TreeRendererInterface {
  /** Render the entire tree to the given container. */
  render(
    container: Container,
    game: ExtensiveFormGame,
    layout: TreeLayout,
    context: RenderContext
  ): void;

  /** Clear all rendered content. */
  clear(container: Container): void;
}
