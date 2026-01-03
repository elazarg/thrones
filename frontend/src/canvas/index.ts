/**
 * Canvas module - centralized exports for game visualization.
 */

// Configuration
export { visualConfig, getPlayerColor, getInfoSetColor } from './config/visualConfig';
export type { VisualConfig } from './config/visualConfig';

// Layout
export { calculateLayout } from './layout/treeLayout';
export type { TreeLayout, NodePosition, EdgePosition } from './layout/treeLayout';
export { calculateMatrixLayout } from './layout/matrixLayout';
export type { MatrixLayout, MatrixCell, MatrixHeader } from './layout/matrixLayout';

// Core
export { SceneGraph, LAYERS } from './core/sceneGraph';
export type { LayerName } from './core/sceneGraph';

// Hooks
export { useCanvas } from './hooks/useCanvas';
export type { ViewMode, UseCanvasOptions, UseCanvasReturn } from './hooks/useCanvas';
export { useLayout } from './hooks/useLayout';
export { useSceneGraph } from './hooks/useSceneGraph';
export { useOverlays } from './hooks/useOverlays';
export { useMatrixOverlays } from './hooks/useMatrixOverlays';

// Renderers
export { TreeRenderer, treeRenderer } from './renderers/TreeRenderer';
export { MatrixRenderer, matrixRenderer } from './renderers/MatrixRenderer';
export type { TreeRendererInterface, RenderContext } from './renderers/types';
export type { MatrixRenderContext } from './renderers/MatrixRenderer';

// Overlays
export { OverlayManager, createDefaultOverlayManager } from './overlays/OverlayManager';
export { EquilibriumOverlay, equilibriumOverlay } from './overlays/EquilibriumOverlay';
export { EdgeProbabilityOverlay, edgeProbabilityOverlay } from './overlays/EdgeProbabilityOverlay';
export { MatrixEquilibriumOverlay, matrixEquilibriumOverlay } from './overlays/MatrixEquilibriumOverlay';
export { MatrixOverlayManager, createDefaultMatrixOverlayManager } from './overlays/MatrixOverlayManager';
export type { Overlay, OverlayContext, MatrixOverlay, MatrixOverlayContext, OverlayData } from './overlays/types';
