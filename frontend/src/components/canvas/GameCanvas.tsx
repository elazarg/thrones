import { useMemo, useState, useEffect } from 'react';
import { useGameStore, useAnalysisStore, useUIStore } from '../../stores';
import { useCanvas } from '../../canvas';
import { ViewFormat, GameFormat, getRequiredGameFormat } from '../../types';
import type { AnyGame } from '../../types';
import './GameCanvas.css';

interface GameCanvasProps {
  /** The view format to render (tree, matrix, or maid) */
  targetViewFormat: ViewFormat;
}

/**
 * GameCanvas component - renders game visualizations.
 * Handles conversion if the target view format requires a different game format.
 */
export function GameCanvas({ targetViewFormat }: GameCanvasProps) {
  const nativeGame = useGameStore((state) => state.currentGame);
  const currentGameId = useGameStore((state) => state.currentGameId);
  const games = useGameStore((state) => state.games);
  const gameLoading = useGameStore((state) => state.gameLoading);
  const fetchConverted = useGameStore((state) => state.fetchConverted);
  const resultsByType = useAnalysisStore((state) => state.resultsByType);
  const selectedAnalysisId = useAnalysisStore((state) => state.selectedAnalysisId);
  const selectedEqIndex = useAnalysisStore((state) => state.selectedEquilibriumIndex);
  const setHoveredNode = useUIStore((state) => state.setHoveredNode);
  const setCurrentViewFormat = useUIStore((state) => state.setCurrentViewFormat);

  // Track the converted game, keyed by game ID
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

  // Determine native game format
  const nativeFormat = useMemo(() => {
    if (!nativeGame) return null;
    return (nativeGame.format_name ?? 'extensive') as GameFormat;
  }, [nativeGame]);

  // Determine if conversion is needed
  const needsConversion = useMemo(() => {
    if (!nativeFormat) return false;

    const requiredFormat = getRequiredGameFormat(targetViewFormat);
    if (!requiredFormat) return false; // Code view doesn't need conversion

    // Check if native format matches required format
    return nativeFormat !== requiredFormat;
  }, [nativeFormat, targetViewFormat]);

  // Get the target game format for conversion
  const targetGameFormat = useMemo(() => {
    if (targetViewFormat === ViewFormat.Tree) return 'extensive';
    if (targetViewFormat === ViewFormat.Matrix) return 'normal';
    if (targetViewFormat === ViewFormat.MAIDDiagram) return 'maid';
    return null;
  }, [targetViewFormat]);

  // Get conversion info from summary
  const conversionInfo = targetGameFormat ? gameSummary?.conversions?.[targetGameFormat] : null;

  // Fetch converted game when needed
  useEffect(() => {
    if (!currentGameId || !needsConversion || !targetGameFormat) {
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

    fetchConverted(currentGameId, targetGameFormat as 'extensive' | 'normal' | 'maid').then((converted) => {
      setConversionState((prev) => {
        if (prev.gameId !== currentGameId) return prev;
        return {
          gameId: currentGameId,
          convertedGame: converted,
          error: converted ? null : 'Conversion failed',
        };
      });
    });
  }, [currentGameId, needsConversion, targetGameFormat, fetchConverted, conversionInfo]);

  // The game to render: converted if needed, otherwise native
  const game = needsConversion ? convertedGame : nativeGame;

  // Map ViewFormat to canvas ViewMode
  const canvasViewMode = useMemo(() => {
    switch (targetViewFormat) {
      case ViewFormat.Tree:
        return 'tree' as const;
      case ViewFormat.Matrix:
        return 'matrix' as const;
      case ViewFormat.MAIDDiagram:
        return 'maid' as const;
      default:
        return 'tree' as const;
    }
  }, [targetViewFormat]);

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

  // Check if selected equilibrium can be visualized in current view
  const equilibriumViewMismatch = useMemo(() => {
    if (!selectedEquilibrium || !selectedAnalysisId) return null;

    const isMAIDAnalysis = selectedAnalysisId.startsWith('maid-');
    const isViewingMAID = targetViewFormat === ViewFormat.MAIDDiagram;
    const isViewingTree = targetViewFormat === ViewFormat.Tree;
    const isViewingMatrix = targetViewFormat === ViewFormat.Matrix;

    // Check if the current game has MAID mappings (from conversion)
    const hasEfgMapping = game && 'maid_to_efg_nodes' in game && game.maid_to_efg_nodes;
    const hasNfgMapping = game && 'maid_decision_to_player' in game && game.maid_decision_to_player;

    if (isMAIDAnalysis && !isViewingMAID) {
      // MAID equilibria can be shown on EFG if the game was converted from MAID
      if (isViewingTree && hasEfgMapping) {
        return null; // EFG mapping exists, can visualize
      }
      // MAID equilibria can be shown on NFG if the game was converted from MAID
      if (isViewingMatrix && hasNfgMapping) {
        return null; // NFG mapping exists, can visualize
      }
      return 'MAID equilibria can only be visualized in MAID view or converted EFG/NFG view. Switch to the MAID, EFG, or NFG tab to see the overlay.';
    }

    // Check if Gambit equilibrium is being viewed on MAID
    // This is now supported - Gambit equilibria can be reverse-mapped to MAID format
    // The MAIDEquilibriumOverlay handles the normalization using the MAID's agent->decision mapping
    if (!isMAIDAnalysis && isViewingMAID) {
      // Allow if the native game format is MAID (we can reverse-map the equilibrium)
      if (nativeFormat === GameFormat.MAID) {
        return null; // Can visualize via reverse mapping
      }
      return 'This equilibrium was computed on a different game format. Switch to EFG or NFG view to see the overlay.';
    }

    return null;
  }, [selectedEquilibrium, selectedAnalysisId, targetViewFormat, game]);

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

  // Flatten results for canvas hook
  const results = useMemo(() => {
    return Object.values(resultsByType).filter((r): r is NonNullable<typeof r> => r !== null);
  }, [resultsByType]);

  // Use canvas hook for rendering
  const { containerRef, fitToView } = useCanvas({
    game,
    results,
    selectedEquilibrium,
    selectedIESDSResult,
    onNodeHover: setHoveredNode,
    viewMode: canvasViewMode,
  });

  // Sync current view format to store
  useEffect(() => {
    setCurrentViewFormat(targetViewFormat);
  }, [targetViewFormat, setCurrentViewFormat]);

  // Determine if we're in a loading state
  const isLoading = gameLoading || (needsConversion && !convertedGame && !conversionError);

  return (
    <div className="game-canvas" ref={containerRef}>
      {isLoading && <div className="canvas-loading">Loading...</div>}
      {!game && !isLoading && !conversionError && (
        <div className="canvas-empty">
          <p>No game selected</p>
          <p className="hint">Upload a .efg, .nfg, .vg, or .json file to get started</p>
        </div>
      )}
      {conversionError && (
        <div className="canvas-error">
          <p>Cannot display this view</p>
          <p className="error-reason">{conversionError}</p>
        </div>
      )}
      {game && !isLoading && (
        <div className="canvas-controls">
          <button className="fit-button" onClick={fitToView} title="Fit to view">
            ⊡
          </button>
        </div>
      )}
      {equilibriumViewMismatch && (
        <div className="canvas-notice">
          <span className="notice-icon">ℹ</span>
          <span className="notice-text">{equilibriumViewMismatch}</span>
        </div>
      )}
    </div>
  );
}
