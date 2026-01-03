/**
 * Canvas module - centralized exports for game visualization.
 */

// Configuration
export { visualConfig, getPlayerColor, getInfoSetColor } from './config/visualConfig';
export type { VisualConfig } from './config/visualConfig';

// Layout
export { calculateLayout } from './layout/treeLayout';
export type { TreeLayout, NodePosition, EdgePosition } from './layout/treeLayout';

// Core
export { SceneGraph, LAYERS } from './core/sceneGraph';
export type { LayerName } from './core/sceneGraph';

// Hooks
export { useCanvas } from './hooks/useCanvas';
export { useLayout } from './hooks/useLayout';
export { useSceneGraph } from './hooks/useSceneGraph';
export { useOverlays } from './hooks/useOverlays';

// Renderers
export { TreeRenderer, treeRenderer } from './renderers/TreeRenderer';
export type { TreeRendererInterface, RenderContext } from './renderers/types';

// Overlays
export { OverlayManager, createDefaultOverlayManager } from './overlays/OverlayManager';
export { EquilibriumOverlay, equilibriumOverlay } from './overlays/EquilibriumOverlay';
export { EdgeProbabilityOverlay, edgeProbabilityOverlay } from './overlays/EdgeProbabilityOverlay';
export type { Overlay, OverlayContext, OverlayData } from './overlays/types';
