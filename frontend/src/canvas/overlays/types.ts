import type { Container } from 'pixi.js';
import type { TreeLayout } from '../layout/treeLayout';
import type { MatrixLayout } from '../layout/matrixLayout';
import type { MAIDLayout } from '../layout/maidLayout';
import type { VisualConfig } from '../config/visualConfig';
import type { ExtensiveFormGame, NormalFormGame, MAIDGame, NashEquilibrium, AnalysisResult, IESDSResult } from '../../types';

// ============================================================================
// Probability thresholds (shared across overlays)
// ============================================================================

/** Probability below this is considered zero */
export const PROBABILITY_EPSILON = 0.001;

/** Probability above this is considered pure (100%) */
export const PURE_STRATEGY_THRESHOLD = 0.999;

/**
 * Context available to tree overlays for computing what to display.
 */
export interface OverlayContext {
  game: ExtensiveFormGame;
  layout: TreeLayout;
  config: VisualConfig;
  players: string[];
  /** Analysis results from the analysis store. */
  analysisResults: AnalysisResult[];
  /** Currently selected equilibrium, if any. */
  selectedEquilibrium: NashEquilibrium | null;
  /** Currently selected IESDS result, if any. */
  selectedIESDSResult: IESDSResult | null;
}

/**
 * Context available to matrix overlays for computing what to display.
 */
export interface MatrixOverlayContext {
  game: NormalFormGame;
  layout: MatrixLayout;
  config: VisualConfig;
  /** Analysis results from the analysis store. */
  analysisResults: AnalysisResult[];
  /** Currently selected equilibrium, if any. */
  selectedEquilibrium: NashEquilibrium | null;
  /** Currently selected IESDS result, if any. */
  selectedIESDSResult: IESDSResult | null;
}

/**
 * Data computed by an overlay, to be applied to the scene.
 * Each overlay type can define its own data structure.
 */
export type OverlayData = unknown;

/**
 * Overlay interface for composable analysis visualizations (tree view).
 * Overlays compute what to display based on context, then apply
 * visual changes to the scene graph.
 */
export interface Overlay {
  /** Unique identifier for this overlay. */
  id: string;

  /** Z-index for layering (higher = on top). */
  zIndex: number;

  /**
   * Compute overlay data from context.
   * Returns null if overlay should not be displayed.
   */
  compute(context: OverlayContext): OverlayData | null;

  /**
   * Apply the overlay to the scene.
   * @param container - Container to add overlay elements to
   * @param data - Data computed by compute()
   * @param config - Visual configuration
   */
  apply(container: Container, data: OverlayData, config: VisualConfig): void;

  /**
   * Clear overlay elements from the scene.
   */
  clear(container: Container): void;
}

/**
 * Overlay interface for matrix view visualizations.
 */
export interface MatrixOverlay {
  /** Unique identifier for this overlay. */
  id: string;

  /** Z-index for layering (higher = on top). */
  zIndex: number;

  /**
   * Compute overlay data from context.
   * Returns null if overlay should not be displayed.
   */
  compute(context: MatrixOverlayContext): OverlayData | null;

  /**
   * Apply the overlay to the scene.
   */
  apply(container: Container, data: OverlayData, config: VisualConfig): void;

  /**
   * Clear overlay elements from the scene.
   */
  clear(container: Container): void;
}

/**
 * Check if two payoff objects match (for equilibrium detection).
 */
export function isMatchingPayoffs(
  outcomePayoffs: Record<string, number>,
  equilibriumPayoffs: Record<string, number>
): boolean {
  const players = Object.keys(equilibriumPayoffs);
  return players.every(
    (player) => Math.abs((outcomePayoffs[player] ?? 0) - equilibriumPayoffs[player]) < PROBABILITY_EPSILON
  );
}

// ============================================================================
// MAID Overlay Types
// ============================================================================

/**
 * Context available to MAID overlays for computing what to display.
 */
export interface MAIDOverlayContext {
  game: MAIDGame;
  layout: MAIDLayout;
  config: VisualConfig;
  agents: string[];
  analysisResults: AnalysisResult[];
  selectedEquilibrium: NashEquilibrium | null;
  selectedIESDSResult: IESDSResult | null;
}

/**
 * Overlay interface for MAID view visualizations.
 */
export interface MAIDOverlay {
  /** Unique identifier for this overlay. */
  id: string;

  /** Z-index for layering (higher = on top). */
  zIndex: number;

  /**
   * Compute overlay data from context.
   * Returns null if overlay should not be displayed.
   */
  compute(context: MAIDOverlayContext): OverlayData | null;

  /**
   * Apply the overlay to the scene.
   */
  apply(container: Container, data: OverlayData, config: VisualConfig): void;

  /**
   * Clear overlay elements from the scene.
   */
  clear(container: Container): void;
}
