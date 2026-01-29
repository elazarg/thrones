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
  const resultsByType = useAnalysisStore((state) => state.resultsByType);
  const selectedAnalysisId = useAnalysisStore((state) => state.selectedAnalysisId);
  const selectedEqIndex = useAnalysisStore((state) => state.selectedEquilibriumIndex);
  const setHoveredNode = useUIStore((state) => state.setHoveredNode);
  const viewModeByGame = useUIStore((state) => state.viewModeByGame);
  const setViewModeForGame = useUIStore((state) => state.setViewModeForGame);
  const setCurrentViewMode = useUIStore((state) => state.setCurrentViewMode);

  // Get view mode override for current game (null = use native view)
  const viewModeOverride = currentGameId ? viewModeByGame[currentGameId] ?? null : null;

  // Track the converted game for non-native view modes, keyed by game ID
  const [conversionState, setConversionState] = useState<{
    gameId: string | null;
    convertedGame: AnyGame | null;
    error: string | null;
  }>({ gameId: null, convertedGame: null, error: null });

  // Get conversion state only if it matches current game
  const convertedGame = conversionState.gameId === currentGameId ? conversionState.convertedGame : null;
  const conversionError = conversionState.gameId === currentGameId ? conversionState.error : null;

  // Get the game summary for conversion info
  const gameSummary = useMemo(() => {
    if (!currentGameId) return null;
    return games.find((g) => g.id === currentGameId) ?? null;
  }, [games, currentGameId]);

  // Determine native format and what formats are available
  // The backend computes chained conversions (e.g., MAID → EFG → NFG, Vegas → MAID → EFG)
  const nativeFormat = gameSummary?.format ?? 'extensive';
  const canConvertToMaid = gameSummary?.conversions?.maid?.possible ?? false;
  const canConvertToExtensive = gameSummary?.conversions?.extensive?.possible ?? false;
  const canConvertToNormal = gameSummary?.conversions?.normal?.possible ?? false;
  const normalConversionBlockers = gameSummary?.conversions?.normal?.blockers ?? [];


  // Determine the target view mode based on override
  const targetViewMode = useMemo(() => {
    if (!nativeGame) return 'tree';
    if (viewModeOverride) return viewModeOverride;
    // Default: native format's natural view
    if (nativeFormat === 'normal') return 'matrix';
    if (nativeFormat === 'maid') return 'maid';
    if (nativeFormat === 'vegas') return 'maid'; // Vegas converts to MAID first
    return 'tree';
  }, [nativeGame, viewModeOverride, nativeFormat]);

  // Determine if we need a converted game
  const needsConversion = useMemo(() => {
    if (!nativeGame) return false;
    // Vegas games always need conversion for visual display
    if (nativeFormat === 'vegas') {
      return true; // Convert to MAID, EFG, or NFG
    }
    // MAID games need conversion when showing as tree or matrix
    if (nativeFormat === 'maid') {
      return targetViewMode === 'tree' || targetViewMode === 'matrix';
    }
    const nativeView = nativeFormat === 'normal' ? 'matrix' : 'tree';
    return targetViewMode !== nativeView;
  }, [nativeGame, nativeFormat, targetViewMode]);

  // Get conversion info for target format
  const targetFormat = targetViewMode === 'matrix' ? 'normal' : targetViewMode === 'maid' ? 'maid' : 'extensive';
  const conversionInfo = gameSummary?.conversions?.[targetFormat];

  // Fetch converted game when needed
  useEffect(() => {
    if (!currentGameId || !needsConversion) {
      setConversionState({ gameId: currentGameId, convertedGame: null, error: null });
      return;
    }

    // Check if conversion is possible before trying
    if (conversionInfo && !conversionInfo.possible) {
      const reason = conversionInfo.blockers?.[0] || 'Conversion not available';
      setConversionState({ gameId: currentGameId, convertedGame: null, error: reason });
      return;
    }

    // Clear error while loading
    setConversionState({ gameId: currentGameId, convertedGame: null, error: null });

    fetchConverted(currentGameId, targetFormat).then((converted) => {
      // Only update if still the same game
      setConversionState((prev) => {
        if (prev.gameId !== currentGameId) return prev;
        return {
          gameId: currentGameId,
          convertedGame: converted,
          error: converted ? null : 'Conversion failed',
        };
      });
    });
  }, [currentGameId, needsConversion, targetFormat, fetchConverted, conversionInfo]);

  // The game to render: converted if needed (with fallback to native on error)
  const game = needsConversion
    ? (convertedGame || (conversionError ? nativeGame : null))
    : nativeGame;

  // Get selected equilibrium if any
  const selectedEquilibrium = useMemo(() => {
    if (selectedEqIndex === null || !selectedAnalysisId) return null;
    const result = resultsByType[selectedAnalysisId];
    const eqs = result?.details.equilibria;
    if (eqs && eqs[selectedEqIndex]) {
      return eqs[selectedEqIndex];
    }
    return null;
  }, [resultsByType, selectedAnalysisId, selectedEqIndex]);

  // Get selected IESDS result if any
  const isIESDSSelected = useAnalysisStore((state) => state.isIESDSSelected);
  const selectedIESDSResult = useMemo(() => {
    if (!isIESDSSelected) return null;
    const iesdsResult = resultsByType['iesds'];
    if (iesdsResult?.details.eliminated !== undefined) {
      return {
        eliminated: iesdsResult.details.eliminated,
        surviving: iesdsResult.details.surviving || {},
        rounds: iesdsResult.details.rounds || 0,
      };
    }
    return null;
  }, [isIESDSSelected, resultsByType]);

  // Flatten results for canvas hook (it expects array)
  const results = useMemo(() => {
    return Object.values(resultsByType).filter((r): r is NonNullable<typeof r> => r !== null);
  }, [resultsByType]);

  // Use canvas hook for all rendering logic
  const { containerRef, fitToView, viewMode } = useCanvas({
    game,
    results,
    selectedEquilibrium,
    selectedIESDSResult,
    onNodeHover: setHoveredNode,
    viewMode: targetViewMode,
  });

  // Sync current view mode to store for other components
  useEffect(() => {
    setCurrentViewMode(viewMode);
  }, [viewMode, setCurrentViewMode]);

  // Reset view mode to native when there's a conversion error
  const handleResetView = useCallback(() => {
    if (currentGameId) {
      setViewModeForGame(currentGameId, null); // null = use native format's natural view
    }
  }, [currentGameId, setViewModeForGame]);

  // Helper to set view mode for current game
  const setViewMode = useCallback((mode: 'tree' | 'matrix' | 'maid' | null) => {
    if (currentGameId) {
      setViewModeForGame(currentGameId, mode);
    }
  }, [currentGameId, setViewModeForGame]);

  return (
    <div className="game-canvas" ref={containerRef}>
      {gameLoading && <div className="canvas-loading">Loading game...</div>}
      {!game && !gameLoading && (
        <div className="canvas-empty">
          <p>No game selected</p>
          <p className="hint">Upload a .efg or .json file to get started</p>
        </div>
      )}
      {conversionError && (
        <div className="canvas-error">
          <p>Cannot show {targetViewMode} view</p>
          <p className="error-reason">{conversionError}</p>
          <button onClick={handleResetView}>
            Show {nativeFormat === 'normal' ? 'matrix' : (nativeFormat === 'maid' || nativeFormat === 'vegas') ? 'MAID' : 'tree'} view
          </button>
        </div>
      )}
      {game && !gameLoading && (
        <div className="canvas-controls">
          <div className="view-toggle">
            <button
              className={`view-toggle-btn ${viewMode === 'maid' ? 'active' : ''}`}
              onClick={() => setViewMode('maid')}
              disabled={nativeFormat !== 'maid' && nativeFormat !== 'vegas' && !canConvertToMaid}
              title={
                nativeFormat === 'maid' || nativeFormat === 'vegas' || canConvertToMaid
                  ? 'MAID diagram view'
                  : 'Cannot convert to MAID'
              }
            >
              <MAIDIcon />
              MAID
            </button>
            <button
              className={`view-toggle-btn ${viewMode === 'tree' ? 'active' : ''}`}
              onClick={() => setViewMode('tree')}
              disabled={nativeFormat !== 'extensive' && !canConvertToExtensive}
              title={
                nativeFormat === 'extensive' || canConvertToExtensive
                  ? 'Extensive form tree view'
                  : 'Cannot convert to extensive form'
              }
            >
              <TreeIcon />
              EFG
            </button>
            <button
              className={`view-toggle-btn ${viewMode === 'matrix' ? 'active' : ''}`}
              onClick={() => setViewMode('matrix')}
              disabled={nativeFormat !== 'normal' && !canConvertToNormal}
              title={
                nativeFormat === 'normal' || canConvertToNormal
                  ? 'Normal form matrix view'
                  : normalConversionBlockers.length > 0
                    ? `Cannot convert: ${normalConversionBlockers[0]}`
                    : 'Cannot convert to normal form'
              }
            >
              <MatrixIcon />
              NFG
            </button>
          </div>
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

/** MAID/influence diagram icon (nodes with directed edges) */
function MAIDIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor" stroke="currentColor" strokeWidth="0.5">
      {/* Decision node (square) */}
      <rect x="1" y="5" width="4" height="4" fill="currentColor" />
      {/* Utility node (diamond) */}
      <polygon points="12,7 10,9 8,7 10,5" fill="currentColor" />
      {/* Chance node (circle) */}
      <circle cx="7" cy="2" r="2" fill="currentColor" />
      {/* Edges */}
      <line x1="7" y1="4" x2="3" y2="5" stroke="currentColor" strokeWidth="1" />
      <line x1="7" y1="4" x2="10" y2="5" stroke="currentColor" strokeWidth="1" />
      <line x1="5" y1="7" x2="8" y2="7" stroke="currentColor" strokeWidth="1" />
    </svg>
  );
}
