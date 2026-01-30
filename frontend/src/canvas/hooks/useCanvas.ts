import { useEffect, useRef, useState, useMemo, useCallback, RefObject } from 'react';
import { Application, Container } from 'pixi.js';
import { Viewport } from 'pixi-viewport';
import { logger } from '../../lib/logger';
import { visualConfig } from '../config/visualConfig';
import { useConfigStore } from '../../stores';
import { getTextResolution, setTextResolution, computeTextResolution } from '../utils/textUtils';
import { calculateLayout } from '../layout/treeLayout';
import { calculateMatrixLayout } from '../layout/matrixLayout';
import { calculateMAIDLayout } from '../layout/maidLayout';
import type { TreeLayout } from '../layout/treeLayout';
import type { MatrixLayout } from '../layout/matrixLayout';
import type { MAIDLayout } from '../layout/maidLayout';
import { treeRenderer } from '../renderers/TreeRenderer';
import { matrixRenderer } from '../renderers/MatrixRenderer';
import { maidRenderer } from '../renderers/MAIDRenderer';
import { useOverlays } from './useOverlays';
import { useMatrixOverlays } from './useMatrixOverlays';
import { useMAIDOverlays } from './useMAIDOverlays';
import type { OverlayContext, MatrixOverlayContext, MAIDOverlayContext } from '../overlays/types';
import type { AnyGame, NashEquilibrium, AnalysisResult, NormalFormGame, ExtensiveFormGame, MAIDGame, IESDSResult } from '../../types';
import { isExtensiveFormGame, isNormalFormGame, isMAIDGame } from '../../types';

const { layout: layoutConfig } = visualConfig;

/** View mode for rendering */
export type ViewMode = 'tree' | 'matrix' | 'maid';

/**
 * Setup or reuse a Viewport with standard configuration.
 * Extracts common viewport initialization logic used by all render functions.
 */
function setupViewport(
  app: Application,
  viewportRef: React.MutableRefObject<Viewport | null>,
  contentContainerRef: React.MutableRefObject<Container | null>,
  worldWidth: number,
  worldHeight: number,
  zoomSpeed: number,
  setZoomResolution: (res: number) => void
): { viewport: Viewport; container: Container; isNew: boolean } {
  let viewport = viewportRef.current;
  let isNew = false;

  if (!viewport) {
    isNew = true;
    viewport = new Viewport({
      screenWidth: app.screen.width,
      screenHeight: app.screen.height,
      worldWidth,
      worldHeight,
      events: app.renderer.events,
    });

    viewport
      .drag()
      .pinch({ percent: visualConfig.viewport.pinchPercent })
      .wheel({ percent: zoomSpeed, smooth: visualConfig.viewport.wheelSmooth })
      .decelerate({ friction: visualConfig.viewport.decelerateFriction })
      .clampZoom({
        minScale: visualConfig.viewport.minScale,
        maxScale: visualConfig.viewport.maxScale,
      });

    viewport.on('zoomed-end', () => {
      const scale = viewport!.scale.x;
      const newRes = computeTextResolution(scale);
      if (newRes !== getTextResolution()) {
        setTextResolution(newRes);
        setZoomResolution(newRes);
      }
    });

    app.stage.addChild(viewport);
    viewportRef.current = viewport;

    const container = new Container();
    container.x = layoutConfig.padding;
    container.y = layoutConfig.padding;
    container.sortableChildren = true;
    viewport.addChild(container);
    contentContainerRef.current = container;
  } else {
    viewport.resize(app.screen.width, app.screen.height, worldWidth, worldHeight);
  }

  return { viewport, container: contentContainerRef.current!, isNew };
}

export interface UseCanvasOptions {
  game: AnyGame | null;
  results: AnalysisResult[];
  selectedEquilibrium: NashEquilibrium | null;
  selectedIESDSResult: IESDSResult | null;
  onNodeHover: (nodeId: string | null) => void;
  viewMode?: ViewMode; // Optional override for view mode
}

export interface UseCanvasReturn {
  containerRef: RefObject<HTMLDivElement | null>;
  isReady: boolean;
  layout: TreeLayout | MatrixLayout | MAIDLayout | null;
  fitToView: () => void;
  viewMode: ViewMode;
  canToggleView: boolean;
}

/**
 * Determine the default view mode for a game.
 */
function getDefaultViewMode(game: AnyGame): ViewMode {
  if (isMAIDGame(game)) {
    return 'maid';
  }
  if (isNormalFormGame(game)) {
    return 'matrix';
  }
  // For extensive form, check if it's a 2-player strategic form (can show as matrix)
  if (game.tags.includes('strategic-form') && game.players.length === 2) {
    return 'matrix';
  }
  return 'tree';
}

/**
 * Check if a game can be shown in both views.
 * Note: For MAID games, this returns false because the actual toggle capability
 * depends on remote conversion availability, which is handled by GameCanvas.tsx.
 */
function canShowBothViews(game: AnyGame): boolean {
  // MAID games can potentially toggle to tree view via conversion
  // but that's handled by GameCanvas.tsx based on conversion availability
  if (isMAIDGame(game)) {
    return false;
  }
  // Normal form games with 2 players can show as matrix
  // Extensive form games can always show as tree
  // Games with strategic-form tag and 2 players can show as both
  if (isNormalFormGame(game)) {
    return false; // Normal form only shows as matrix for now
  }
  // Extensive form games with strategic-form tag can potentially show as matrix too
  return game.tags.includes('strategic-form') && game.players.length === 2;
}

/**
 * Main hook for canvas lifecycle and rendering.
 * Supports both tree and matrix rendering based on game type.
 */
export function useCanvas(options: UseCanvasOptions): UseCanvasReturn {
  const { game, results, selectedEquilibrium, selectedIESDSResult, onNodeHover, viewMode: viewModeOverride } = options;

  const containerRef = useRef<HTMLDivElement | null>(null);
  const appRef = useRef<Application | null>(null);
  const viewportRef = useRef<Viewport | null>(null);
  const contentContainerRef = useRef<Container | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [zoomResolution, setZoomResolution] = useState(getTextResolution);

  const { updateOverlays } = useOverlays();
  const { updateMatrixOverlays } = useMatrixOverlays();
  const { updateMAIDOverlays } = useMAIDOverlays();

  // Get configurable zoom speed from config store
  const zoomSpeed = useConfigStore((state) => state.zoomSpeed);

  // Determine view mode
  const viewMode = useMemo(() => {
    if (!game) return 'tree';
    if (viewModeOverride) return viewModeOverride;
    return getDefaultViewMode(game);
  }, [game, viewModeOverride]);

  // Check if view can be toggled
  const canToggleView = useMemo(() => {
    if (!game) return false;
    return canShowBothViews(game);
  }, [game]);

  const extensiveGame = useMemo((): ExtensiveFormGame | null => {
    if (!game || viewMode !== 'tree') return null;
    if (!isExtensiveFormGame(game)) return null;
    return game;
  }, [game, viewMode]);

  const normalFormGame = useMemo((): NormalFormGame | null => {
    if (!game || viewMode !== 'matrix') return null;
    if (!isNormalFormGame(game)) return null;
    return game;
  }, [game, viewMode]);

  const maidGame = useMemo((): MAIDGame | null => {
    if (!game || viewMode !== 'maid') return null;
    if (!isMAIDGame(game)) return null;
    return game;
  }, [game, viewMode]);

// Calculate tree layout (depends on guarded extensiveGame)
  const treeLayout = useMemo(() => {
    if (!extensiveGame) return null;
    return calculateLayout(extensiveGame);
  }, [extensiveGame]);

  // Calculate matrix layout (depends on guarded normalFormGame)
  const matrixLayout = useMemo(() => {
    if (!normalFormGame) return null;
    return calculateMatrixLayout(normalFormGame);
  }, [normalFormGame]);

  // Calculate MAID layout (depends on guarded maidGame)
  const maidLayout = useMemo(() => {
    if (!maidGame) return null;
    return calculateMAIDLayout(maidGame);
  }, [maidGame]);

  // Get the active layout
  const layout = viewMode === 'tree' ? treeLayout : viewMode === 'matrix' ? matrixLayout : maidLayout;

  // Prevent browser zoom on canvas
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const preventZoom = (e: WheelEvent) => {
      if (e.ctrlKey) e.preventDefault();
    };

    const preventTouchZoom = (e: TouchEvent) => {
      if (e.touches.length > 1) e.preventDefault();
    };

    container.addEventListener('wheel', preventZoom, { passive: false });
    container.addEventListener('touchmove', preventTouchZoom, { passive: false });

    return () => {
      container.removeEventListener('wheel', preventZoom);
      container.removeEventListener('touchmove', preventTouchZoom);
    };
  }, []);

  // Initialize Pixi application
  useEffect(() => {
    if (!containerRef.current) return;

    let cancelled = false;
    const app = new Application();

    const initApp = async () => {
      try {
        await app.init({
          background: visualConfig.background,
          resizeTo: containerRef.current!,
          antialias: true,
          resolution: window.devicePixelRatio || 1,
          autoDensity: true,
        });

        if (cancelled) {
          app.destroy(true);
          return;
        }

        containerRef.current!.appendChild(app.canvas);
        appRef.current = app;
        setIsReady(true);
      } catch (err) {
        logger.error('Failed to initialize Pixi:', err);
      }
    };

    initApp();

    return () => {
      cancelled = true;
      setIsReady(false);
      if (viewportRef.current) {
        viewportRef.current.destroy();
        viewportRef.current = null;
      }
      if (appRef.current) {
        appRef.current.destroy(true, { children: true });
        appRef.current = null;
      }
    };
  }, []);

  // Render game tree (extensive form)
  const renderTree = useCallback(() => {
    const app = appRef.current;
    if (!app || !app.stage || !treeLayout || !extensiveGame) return;

    // 1. Setup or reuse Viewport
    const worldWidth = treeLayout.width + layoutConfig.padding * 2;
    const worldHeight = treeLayout.height + layoutConfig.padding * 2;
    const { container } = setupViewport(
      app, viewportRef, contentContainerRef,
      worldWidth, worldHeight, zoomSpeed, setZoomResolution
    );

    // 2. Clear previous content
    container.removeChildren();

    // 3. Render tree
    treeRenderer.render(container, extensiveGame, treeLayout, {
      config: visualConfig,
      players: extensiveGame.players,
      onNodeHover,
    });

    // 4. Apply overlays
    const overlayContext: OverlayContext = {
      game: extensiveGame,
      layout: treeLayout,
      config: visualConfig,
      players: extensiveGame.players,
      analysisResults: results,
      selectedEquilibrium,
      selectedIESDSResult,
    };
    updateOverlays(container, overlayContext);

  }, [treeLayout, extensiveGame, selectedEquilibrium, selectedIESDSResult, onNodeHover, results, updateOverlays, zoomResolution, zoomSpeed]);

  // Render matrix (normal form)
  const renderMatrix = useCallback(() => {
    const app = appRef.current;
    if (!app || !app.stage || !matrixLayout || !normalFormGame) return;

    // 1. Setup or reuse Viewport
    const worldWidth = matrixLayout.width + layoutConfig.padding * 2;
    const worldHeight = matrixLayout.height + layoutConfig.padding * 2;
    const { container } = setupViewport(
      app, viewportRef, contentContainerRef,
      worldWidth, worldHeight, zoomSpeed, setZoomResolution
    );

    // 2. Clear content
    container.removeChildren();

    // 3. Render matrix
    matrixRenderer.render(container, normalFormGame, matrixLayout, {
      config: visualConfig,
    });

    // 4. Apply overlays
    const matrixOverlayContext: MatrixOverlayContext = {
      game: normalFormGame,
      layout: matrixLayout,
      config: visualConfig,
      analysisResults: results,
      selectedEquilibrium,
      selectedIESDSResult,
    };
    updateMatrixOverlays(container, matrixOverlayContext);

  }, [matrixLayout, normalFormGame, selectedEquilibrium, selectedIESDSResult, results, updateMatrixOverlays, zoomResolution, zoomSpeed]);

  // Render MAID (Multi-Agent Influence Diagram)
  const renderMAID = useCallback(() => {
    const app = appRef.current;
    if (!app || !app.stage || !maidLayout || !maidGame) return;

    // 1. Setup or reuse Viewport
    const worldWidth = maidLayout.width + layoutConfig.padding * 2;
    const worldHeight = maidLayout.height + layoutConfig.padding * 2;
    const { container } = setupViewport(
      app, viewportRef, contentContainerRef,
      worldWidth, worldHeight, zoomSpeed, setZoomResolution
    );

    // 2. Clear content
    container.removeChildren();

    // 3. Render MAID
    maidRenderer.render(container, maidGame, maidLayout, {
      config: visualConfig,
      agents: maidGame.agents,
      onNodeHover,
    });

    // 4. Apply overlays
    const maidOverlayContext: MAIDOverlayContext = {
      game: maidGame,
      layout: maidLayout,
      config: visualConfig,
      agents: maidGame.agents,
      analysisResults: results,
      selectedEquilibrium,
      selectedIESDSResult,
    };
    updateMAIDOverlays(container, maidOverlayContext);

  }, [maidLayout, maidGame, selectedEquilibrium, selectedIESDSResult, onNodeHover, results, updateMAIDOverlays, zoomResolution, zoomSpeed]);

  // Trigger render when ready or dependencies change
  useEffect(() => {
    if (isReady && game) {
      if (viewMode === 'tree' && extensiveGame && treeLayout) {
        renderTree();
      } else if (viewMode === 'matrix' && normalFormGame && matrixLayout) {
        renderMatrix();
      } else if (viewMode === 'maid' && maidGame && maidLayout) {
        renderMAID();
      }
    }
  }, [isReady, game, viewMode, extensiveGame, normalFormGame, maidGame, treeLayout, matrixLayout, maidLayout, renderTree, renderMatrix, renderMAID]);

  // Fit to view handler
  const fitToView = useCallback(() => {
    if (!viewportRef.current || !layout) return;

    const worldWidth = layout.width + layoutConfig.padding * 2;
    const worldHeight = layout.height + layoutConfig.padding * 2;
    viewportRef.current.fit(true, worldWidth, worldHeight);
    viewportRef.current.moveCenter(worldWidth / 2, worldHeight / 2);
  }, [layout]);

  // Automatically fit to view when layout changes (new game or view mode switch)
  useEffect(() => {
    if (isReady && layout && viewportRef.current) {
      fitToView();
    }
  }, [isReady, layout, fitToView]); // layout changes only when game/viewMode changes
  
  return {
    containerRef,
    isReady,
    layout,
    fitToView,
    viewMode,
    canToggleView,
  };
}
