import { useMemo } from 'react';
import { ErrorBoundary, ErrorFallback } from '../ErrorBoundary';
import { GameCanvas } from '../canvas/GameCanvas';
import { CodeEditor } from '../editor/CodeEditor';
import { AnalysisPanel } from '../panels/AnalysisPanel';
import { useUIStore, useGameStore } from '../../stores';
import {
  ViewFormat,
  GameFormat,
  getNativeViewFormat,
  isVegasGame,
} from '../../types';
import './MainLayout.css';

/**
 * Get available view format tabs for a game based on its format and conversions.
 */
function getAvailableTabs(
  gameFormat: GameFormat,
  conversions: Record<string, { possible: boolean }> | undefined
): { format: ViewFormat; label: string; enabled: boolean }[] {
  const tabs: { format: ViewFormat; label: string; enabled: boolean }[] = [];

  // Add tabs based on game format
  switch (gameFormat) {
    case GameFormat.Vegas:
      tabs.push({ format: ViewFormat.Code, label: 'Code', enabled: true });
      tabs.push({
        format: ViewFormat.MAIDDiagram,
        label: 'MAID',
        enabled: conversions?.maid?.possible ?? false,
      });
      tabs.push({
        format: ViewFormat.Tree,
        label: 'EFG',
        enabled: conversions?.extensive?.possible ?? false,
      });
      tabs.push({
        format: ViewFormat.Matrix,
        label: 'NFG',
        enabled: conversions?.normal?.possible ?? false,
      });
      break;

    case GameFormat.MAID:
      tabs.push({ format: ViewFormat.MAIDDiagram, label: 'MAID', enabled: true });
      tabs.push({
        format: ViewFormat.Tree,
        label: 'EFG',
        enabled: conversions?.extensive?.possible ?? false,
      });
      tabs.push({
        format: ViewFormat.Matrix,
        label: 'NFG',
        enabled: conversions?.normal?.possible ?? false,
      });
      break;

    case GameFormat.Extensive:
      tabs.push({ format: ViewFormat.Tree, label: 'EFG', enabled: true });
      tabs.push({
        format: ViewFormat.Matrix,
        label: 'NFG',
        enabled: conversions?.normal?.possible ?? false,
      });
      break;

    case GameFormat.Normal:
      tabs.push({ format: ViewFormat.Matrix, label: 'NFG', enabled: true });
      tabs.push({
        format: ViewFormat.Tree,
        label: 'EFG',
        enabled: conversions?.extensive?.possible ?? false,
      });
      break;
  }

  return tabs;
}

export function MainLayout() {
  const currentGame = useGameStore((s) => s.currentGame);
  const currentGameId = useGameStore((s) => s.currentGameId);
  const games = useGameStore((s) => s.games);

  const viewFormatByGame = useUIStore((s) => s.viewFormatByGame);
  const setViewFormatForGame = useUIStore((s) => s.setViewFormatForGame);

  // Get game format and summary (for conversion info)
  const gameFormat = useMemo(() => {
    if (!currentGame) return null;
    const formatName = currentGame.format_name ?? 'extensive';
    return formatName as GameFormat;
  }, [currentGame]);

  const gameSummary = useMemo(() => {
    if (!currentGameId) return null;
    return games.find((g) => g.id === currentGameId) ?? null;
  }, [games, currentGameId]);

  // Determine the active view format
  const activeViewFormat = useMemo(() => {
    if (!currentGameId || !gameFormat) return ViewFormat.Tree;

    // Check for user override
    const override = viewFormatByGame[currentGameId];
    if (override) return override;

    // Use native view for the game format
    return getNativeViewFormat(gameFormat);
  }, [currentGameId, gameFormat, viewFormatByGame]);

  // Get available tabs
  const tabs = useMemo(() => {
    if (!gameFormat) return [];
    return getAvailableTabs(gameFormat, gameSummary?.conversions);
  }, [gameFormat, gameSummary?.conversions]);

  // Get source code for Vegas games
  const gameSourceCode = currentGame && isVegasGame(currentGame) ? currentGame.source_code : null;

  // Handle tab click
  const handleTabClick = (format: ViewFormat) => {
    if (currentGameId) {
      // If clicking the native format, clear the override
      if (gameFormat && format === getNativeViewFormat(gameFormat)) {
        setViewFormatForGame(currentGameId, null);
      } else {
        setViewFormatForGame(currentGameId, format);
      }
    }
  };

  // Determine what to render
  const renderContent = () => {
    if (activeViewFormat === ViewFormat.Code) {
      return (
        <ErrorBoundary name="CodeEditor">
          <CodeEditor
            value={gameSourceCode ?? '// No source code available'}
            readOnly={true}
          />
        </ErrorBoundary>
      );
    }

    // All other views use the canvas
    return (
      <ErrorBoundary name="GameCanvas">
        <GameCanvas targetViewFormat={activeViewFormat} />
      </ErrorBoundary>
    );
  };

  return (
    <main className="main-layout">
      <section className="canvas-section">
        <div className="canvas-toolbar">
          <div className="view-tabs">
            {tabs.map((tab) => (
              <button
                key={tab.format}
                className={`view-tab ${activeViewFormat === tab.format ? 'active' : ''}`}
                onClick={() => handleTabClick(tab.format)}
                disabled={!tab.enabled}
                title={tab.enabled ? `View as ${tab.label}` : `Cannot convert to ${tab.label}`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
        <div className="canvas-content">
          {renderContent()}
        </div>
      </section>
      <aside className="panel-section">
        <ErrorBoundary
          name="AnalysisPanel"
          fallback={<ErrorFallback message="Failed to load analysis panel" />}
        >
          <AnalysisPanel />
        </ErrorBoundary>
      </aside>
    </main>
  );
}
