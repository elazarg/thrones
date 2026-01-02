import { useEffect, useRef, useState, useMemo, useCallback, RefObject } from 'react';
import { Application, Container } from 'pixi.js';
import { Viewport } from 'pixi-viewport';
import { visualConfig } from '../config/visualConfig';
import { calculateLayout } from '../layout/treeLayout';
import type { TreeLayout } from '../layout/treeLayout';
import { treeRenderer } from '../renderers/TreeRenderer';
import { useOverlays } from './useOverlays';
import type { OverlayContext } from '../overlays/types';
import type { Game, NashEquilibrium, AnalysisResult } from '../../types';

const { layout: layoutConfig } = visualConfig;

export interface UseCanvasOptions {
  game: Game | null;
  results: AnalysisResult[];
  selectedEquilibrium: NashEquilibrium | null;
  onNodeHover: (nodeId: string | null) => void;
}

export interface UseCanvasReturn {
  containerRef: RefObject<HTMLDivElement | null>;
  isReady: boolean;
  layout: TreeLayout | null;
  fitToView: () => void;
}

/**
 * Main hook for canvas lifecycle and rendering.
 * Composes Pixi.js initialization, tree rendering, and overlay management.
 */
export function useCanvas(options: UseCanvasOptions): UseCanvasReturn {
  const { game, results, selectedEquilibrium, onNodeHover } = options;

  const containerRef = useRef<HTMLDivElement | null>(null);
  const appRef = useRef<Application | null>(null);
  const viewportRef = useRef<Viewport | null>(null);
  const [isReady, setIsReady] = useState(false);

  const { updateOverlays } = useOverlays();

  // Calculate layout when game changes
  const layout = useMemo(() => {
    if (!game) return null;
    return calculateLayout(game);
  }, [game]);

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

  // Render game tree
  const renderTree = useCallback(() => {
    const app = appRef.current;
    if (!app || !app.stage || !layout || !game) return;

    // Clear previous content
    app.stage.removeChildren();
    if (viewportRef.current) {
      viewportRef.current.destroy();
      viewportRef.current = null;
    }

    // Create viewport
    const worldWidth = layout.width + layoutConfig.padding * 2;
    const worldHeight = layout.height + layoutConfig.padding * 2;

    const viewport = new Viewport({
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

    // Create content container
    const container = new Container();
    container.x = layoutConfig.padding;
    container.y = layoutConfig.padding;
    container.sortableChildren = true;
    viewport.addChild(container);

    // Render tree
    treeRenderer.render(container, game, layout, {
      config: visualConfig,
      players: game.players,
      onNodeHover,
    });

    // Apply overlays
    const overlayContext: OverlayContext = {
      game,
      layout,
      config: visualConfig,
      players: game.players,
      analysisResults: results,
      selectedEquilibrium,
    };
    updateOverlays(container, overlayContext);

    // Fit to view
    viewport.fit(true, worldWidth, worldHeight);
    viewport.moveCenter(worldWidth / 2, worldHeight / 2);
  }, [layout, game, selectedEquilibrium, onNodeHover, results, updateOverlays]);

  // Trigger render when ready or dependencies change
  useEffect(() => {
    if (isReady) {
      renderTree();
    }
  }, [isReady, renderTree]);

  // Fit to view handler
  const fitToView = useCallback(() => {
    if (viewportRef.current && layout) {
      const worldWidth = layout.width + layoutConfig.padding * 2;
      const worldHeight = layout.height + layoutConfig.padding * 2;
      viewportRef.current.fit(true, worldWidth, worldHeight);
      viewportRef.current.moveCenter(worldWidth / 2, worldHeight / 2);
    }
  }, [layout]);

  return {
    containerRef,
    isReady,
    layout,
    fitToView,
  };
}
