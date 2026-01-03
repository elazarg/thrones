import { useMemo, useCallback } from 'react';
import { useGameStore, useAnalysisStore, useUIStore } from '../../stores';
import { useCanvas } from '../../canvas';
import './GameCanvas.css';

/**
 * GameCanvas component - main visualization of game trees.
 * Uses the useCanvas hook for all Pixi.js lifecycle and rendering.
 */
export function GameCanvas() {
  const game = useGameStore((state) => state.currentGame);
  const gameLoading = useGameStore((state) => state.gameLoading);
  const results = useAnalysisStore((state) => state.results);
  const selectedEqIndex = useAnalysisStore((state) => state.selectedEquilibriumIndex);
  const setHoveredNode = useUIStore((state) => state.setHoveredNode);
  const viewModeOverride = useUIStore((state) => state.viewModeOverride);
  const toggleViewMode = useUIStore((state) => state.toggleViewMode);

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
  const { containerRef, fitToView, viewMode, canToggleView } = useCanvas({
    game,
    results,
    selectedEquilibrium,
    onNodeHover: setHoveredNode,
    viewMode: viewModeOverride ?? undefined,
  });

  // Handle view toggle
  const handleToggleView = useCallback(() => {
    toggleViewMode(viewMode, canToggleView);
  }, [toggleViewMode, viewMode, canToggleView]);

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
          {canToggleView && (
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
