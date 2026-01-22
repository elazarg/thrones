import { useMemo, useCallback, useState, useEffect } from 'react';
import { useGameStore, useAnalysisStore, useUIStore } from '../../stores';
import { useCanvas } from '../../canvas';
import type { AnyGame } from '../../types';
import './GameCanvas.css';

/**
 * GameCanvas component - main visualization of game trees.
 * Uses the useCanvas hook for all Pixi.js lifecycle and rendering.
 */
export function GameCanvas() {
  const nativeGame = useGameStore((state) => state.currentGame);
  const currentGameId = useGameStore((state) => state.currentGameId);
  const games = useGameStore((state) => state.games);
  const gameLoading = useGameStore((state) => state.gameLoading);
  const fetchConverted = useGameStore((state) => state.fetchConverted);
  const results = useAnalysisStore((state) => state.results);
  const selectedEqIndex = useAnalysisStore((state) => state.selectedEquilibriumIndex);
  const setHoveredNode = useUIStore((state) => state.setHoveredNode);
  const viewModeOverride = useUIStore((state) => state.viewModeOverride);
  const toggleViewMode = useUIStore((state) => state.toggleViewMode);

  // Track the converted game for non-native view modes
  const [convertedGame, setConvertedGame] = useState<AnyGame | null>(null);

  // Get the game summary for conversion info
  const gameSummary = useMemo(() => {
    if (!currentGameId) return null;
    return games.find((g) => g.id === currentGameId) ?? null;
  }, [games, currentGameId]);

  // Determine native format and what formats are available
  const nativeFormat = gameSummary?.format ?? 'extensive';
  const canConvertToExtensive = gameSummary?.conversions?.extensive?.possible ?? false;
  const canConvertToNormal = gameSummary?.conversions?.normal?.possible ?? false;

  // Can we toggle between views?
  const canToggle = nativeFormat === 'extensive' ? canConvertToNormal : canConvertToExtensive;

  // Determine the target view mode based on override
  const targetViewMode = useMemo(() => {
    if (!nativeGame) return 'tree';
    if (viewModeOverride) return viewModeOverride;
    // Default: native format's natural view
    return nativeFormat === 'normal' ? 'matrix' : 'tree';
  }, [nativeGame, viewModeOverride, nativeFormat]);

  // Determine if we need a converted game
  const needsConversion = useMemo(() => {
    if (!nativeGame) return false;
    const nativeView = nativeFormat === 'normal' ? 'matrix' : 'tree';
    return targetViewMode !== nativeView;
  }, [nativeGame, nativeFormat, targetViewMode]);

  // Fetch converted game when needed
  useEffect(() => {
    if (!currentGameId || !needsConversion) {
      setConvertedGame(null);
      return;
    }

    const targetFormat = targetViewMode === 'matrix' ? 'normal' : 'extensive';
    fetchConverted(currentGameId, targetFormat).then((converted) => {
      setConvertedGame(converted);
    });
  }, [currentGameId, needsConversion, targetViewMode, fetchConverted]);

  // The game to render: converted if needed, otherwise native
  const game = needsConversion ? convertedGame : nativeGame;

  // Get selected equilibrium if any
  const selectedEquilibrium = useMemo(() => {
    if (selectedEqIndex === null) return null;
    for (const result of results) {
      const eqs = result.details.equilibria;
      if (eqs && eqs[selectedEqIndex]) {
        return eqs[selectedEqIndex];
      }
    }
    return null;
  }, [results, selectedEqIndex]);

  // Use canvas hook for all rendering logic
  const { containerRef, fitToView, viewMode } = useCanvas({
    game,
    results,
    selectedEquilibrium,
    onNodeHover: setHoveredNode,
    viewMode: targetViewMode,
  });

  // Handle view toggle
  const handleToggleView = useCallback(() => {
    toggleViewMode(viewMode, canToggle);
  }, [toggleViewMode, viewMode, canToggle]);

  return (
    <div className="game-canvas" ref={containerRef}>
      {gameLoading && <div className="canvas-loading">Loading game...</div>}
      {!game && !gameLoading && (
        <div className="canvas-empty">
          <p>No game selected</p>
          <p className="hint">Upload a .efg or .json file to get started</p>
        </div>
      )}
      {game && !gameLoading && (
        <div className="canvas-controls">
          {canToggle && (
            <div className="view-toggle" title="Toggle view mode">
              <button
                className={`view-toggle-btn ${viewMode === 'tree' ? 'active' : ''}`}
                onClick={() => viewMode !== 'tree' && handleToggleView()}
                title="Tree view"
              >
                <TreeIcon />
              </button>
              <button
                className={`view-toggle-btn ${viewMode === 'matrix' ? 'active' : ''}`}
                onClick={() => viewMode !== 'matrix' && handleToggleView()}
                title="Matrix view"
              >
                <MatrixIcon />
              </button>
            </div>
          )}
          <button className="fit-button" onClick={fitToView} title="Fit to view">
            ⊡
          </button>
        </div>
      )}
    </div>
  );
}

/** Simple tree icon */
function TreeIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
      <circle cx="7" cy="2" r="1.5" />
      <circle cx="3" cy="8" r="1.5" />
      <circle cx="11" cy="8" r="1.5" />
      <circle cx="1" cy="12" r="1.5" />
      <circle cx="5" cy="12" r="1.5" />
      <circle cx="9" cy="12" r="1.5" />
      <circle cx="13" cy="12" r="1.5" />
      <line x1="7" y1="3.5" x2="3" y2="6.5" stroke="currentColor" strokeWidth="1" />
      <line x1="7" y1="3.5" x2="11" y2="6.5" stroke="currentColor" strokeWidth="1" />
      <line x1="3" y1="9.5" x2="1" y2="10.5" stroke="currentColor" strokeWidth="1" />
      <line x1="3" y1="9.5" x2="5" y2="10.5" stroke="currentColor" strokeWidth="1" />
      <line x1="11" y1="9.5" x2="9" y2="10.5" stroke="currentColor" strokeWidth="1" />
      <line x1="11" y1="9.5" x2="13" y2="10.5" stroke="currentColor" strokeWidth="1" />
    </svg>
  );
}

/** Simple matrix/grid icon */
function MatrixIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.2">
      <rect x="1" y="1" width="12" height="12" rx="1" />
      <line x1="1" y1="5" x2="13" y2="5" />
      <line x1="1" y1="9" x2="13" y2="9" />
      <line x1="5" y1="1" x2="5" y2="13" />
      <line x1="9" y1="1" x2="9" y2="13" />
    </svg>
  );
}
