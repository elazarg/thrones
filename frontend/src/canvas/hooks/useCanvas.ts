import { useEffect, useRef, useState, useMemo, useCallback, RefObject } from 'react';
import { Application, Container } from 'pixi.js';
import { Viewport } from 'pixi-viewport';
import { visualConfig } from '../config/visualConfig';
import { calculateLayout } from '../layout/treeLayout';
import { calculateMatrixLayout } from '../layout/matrixLayout';
import type { TreeLayout } from '../layout/treeLayout';
import type { MatrixLayout } from '../layout/matrixLayout';
import { treeRenderer } from '../renderers/TreeRenderer';
import { matrixRenderer } from '../renderers/MatrixRenderer';
import { useOverlays } from './useOverlays';
import { useMatrixOverlays } from './useMatrixOverlays';
import type { OverlayContext, MatrixOverlayContext } from '../overlays/types';
import type { AnyGame, NashEquilibrium, AnalysisResult, NormalFormGame, ExtensiveFormGame, IESDSResult } from '../../types';
import { isExtensiveFormGame, isNormalFormGame } from '../../types';

const { layout: layoutConfig } = visualConfig;

/** View mode for rendering */
export type ViewMode = 'tree' | 'matrix';

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
  layout: TreeLayout | MatrixLayout | null;
  fitToView: () => void;
  viewMode: ViewMode;
  canToggleView: boolean;
}

/**
 * Determine the default view mode for a game.
 */
function getDefaultViewMode(game: AnyGame): ViewMode {
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
 */
function canShowBothViews(game: AnyGame): boolean {
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

  const { updateOverlays } = useOverlays();
  const { updateMatrixOverlays } = useMatrixOverlays();

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

  // Get the active layout
  const layout = viewMode === 'tree' ? treeLayout : matrixLayout;

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
        console.error('Failed to initialize Pixi:', err);
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
  // Render game tree (extensive form)
  const renderTree = useCallback(() => {
    const app = appRef.current;
    if (!app || !app.stage || !treeLayout || !extensiveGame) return;

    // 1. Setup or reuse Viewport
    let viewport = viewportRef.current;
    const worldWidth = treeLayout.width + layoutConfig.padding * 2;
    const worldHeight = treeLayout.height + layoutConfig.padding * 2;

    if (!viewport) {
      // Create Viewport only if it doesn't exist
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
        .wheel({ percent: visualConfig.viewport.wheelPercent, smooth: visualConfig.viewport.wheelSmooth })
        .decelerate({ friction: visualConfig.viewport.decelerateFriction });

      app.stage.addChild(viewport);
      viewportRef.current = viewport;

      const container = new Container();
      container.x = layoutConfig.padding;
      container.y = layoutConfig.padding;
      container.sortableChildren = true;
      viewport.addChild(container);
      contentContainerRef.current = container;
    } else {
      // Update world size for existing viewport
      viewport.resize(app.screen.width, app.screen.height, worldWidth, worldHeight);
    }

    // 2. Clear previous content (BUT KEEP VIEWPORT)
    const container = contentContainerRef.current!;
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

  }, [treeLayout, extensiveGame, selectedEquilibrium, selectedIESDSResult, onNodeHover, results, updateOverlays]);

  // Render matrix (normal form)
  const renderMatrix = useCallback(() => {
    const app = appRef.current;
    if (!app || !app.stage || !matrixLayout || !normalFormGame) return;

    // 1. Setup or reuse Viewport
    let viewport = viewportRef.current;
    const worldWidth = matrixLayout.width + layoutConfig.padding * 2;
    const worldHeight = matrixLayout.height + layoutConfig.padding * 2;

    if (!viewport) {
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
        .wheel({ percent: visualConfig.viewport.wheelPercent, smooth: visualConfig.viewport.wheelSmooth })
        .decelerate({ friction: visualConfig.viewport.decelerateFriction });

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

    // 2. Clear content
    const container = contentContainerRef.current!;
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

  }, [matrixLayout, normalFormGame, selectedEquilibrium, selectedIESDSResult, results, updateMatrixOverlays]);
  
  // Trigger render when ready or dependencies change
  useEffect(() => {
    if (isReady && game) {
      if (viewMode === 'tree' && extensiveGame && treeLayout) {
        renderTree();
      } else if (viewMode === 'matrix' && normalFormGame && matrixLayout) {
        renderMatrix();
      }
    }
  }, [isReady, game, viewMode, extensiveGame, normalFormGame, treeLayout, matrixLayout, renderTree, renderMatrix]);

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
