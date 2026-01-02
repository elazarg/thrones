import { useMemo } from 'react';
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
  const { containerRef, fitToView } = useCanvas({
    game,
    results,
    selectedEquilibrium,
    onNodeHover: setHoveredNode,
  });

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
          <button className="fit-button" onClick={fitToView} title="Fit to view">
            ⊡
          </button>
        </div>
      )}
    </div>
  );
}
