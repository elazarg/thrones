import { useRef, useEffect, useCallback, useState } from 'react';
import { Application } from 'pixi.js';
import { logger } from '../../lib/logger';
import { SceneGraph } from '../core/sceneGraph';
import { visualConfig } from '../config/visualConfig';

interface UseSceneGraphOptions {
  containerRef: React.RefObject<HTMLDivElement | null>;
  worldWidth: number;
  worldHeight: number;
}

interface UseSceneGraphResult {
  sceneGraph: SceneGraph | null;
  isReady: boolean;
  fitToView: () => void;
}

/**
 * Hook that manages the Pixi.js Application and SceneGraph lifecycle.
 * Handles initialization, cleanup, and provides scene access.
 */
export function useSceneGraph({
  containerRef,
  worldWidth,
  worldHeight,
}: UseSceneGraphOptions): UseSceneGraphResult {
  const appRef = useRef<Application | null>(null);
  const sceneGraphRef = useRef<SceneGraph | null>(null);
  const [isReady, setIsReady] = useState(false);

  // Initialize Pixi application and scene graph
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

        // Create scene graph
        const sceneGraph = new SceneGraph(app, worldWidth, worldHeight);
        sceneGraphRef.current = sceneGraph;

        setIsReady(true);
      } catch (err) {
        logger.error('Failed to initialize Pixi:', err);
      }
    };

    initApp();

    return () => {
      cancelled = true;
      setIsReady(false);

      if (sceneGraphRef.current) {
        sceneGraphRef.current.destroy();
        sceneGraphRef.current = null;
      }

      if (appRef.current) {
        appRef.current.destroy(true, { children: true });
        appRef.current = null;
      }
    };
  }, [containerRef, worldWidth, worldHeight]);

  // Fit to view callback
  const fitToView = useCallback(() => {
    if (sceneGraphRef.current) {
      sceneGraphRef.current.fitToView(worldWidth, worldHeight);
    }
  }, [worldWidth, worldHeight]);

  return {
    sceneGraph: sceneGraphRef.current,
    isReady,
    fitToView,
  };
}
