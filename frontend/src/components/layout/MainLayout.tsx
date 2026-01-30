import { useMemo, useEffect, useCallback } from 'react';
import { ErrorBoundary, ErrorFallback } from '../ErrorBoundary';
import { GameCanvas } from '../canvas/GameCanvas';
import { CodeEditor } from '../editor/CodeEditor';
import { AnalysisPanel } from '../panels/AnalysisPanel';
import { useUIStore, useGameStore, usePluginStore } from '../../stores';
import {
  ViewFormat,
  GameFormat,
  getNativeViewFormat,
  isVegasGame,
} from '../../types';
import './MainLayout.css';

/** Tab representing a compiled code output. */
interface CompiledTab {
  targetId: string;
  label: string;
  language: string;
}

/**
 * Get available view format tabs for a game based on its format and conversions.
 * All 4 model tabs always appear (some may be disabled based on format/conversions).
 */
function getAvailableTabs(
  gameFormat: GameFormat,
  conversions: Record<string, { possible: boolean }> | undefined
): { format: ViewFormat; label: string; enabled: boolean; disabledReason?: string }[] {
  // Helper to check if conversion is possible
  const canConvert = (target: string) => conversions?.[target]?.possible ?? false;

  // Determine which tabs are enabled based on game format
  const isNative = (format: ViewFormat) => {
    switch (gameFormat) {
      case GameFormat.Vegas: return format === ViewFormat.Code;
      case GameFormat.MAID: return format === ViewFormat.MAIDDiagram;
      case GameFormat.Extensive: return format === ViewFormat.Tree;
      case GameFormat.Normal: return format === ViewFormat.Matrix;
      default: return false;
    }
  };

  const isEnabled = (format: ViewFormat) => {
    if (isNative(format)) return true;
    switch (format) {
      case ViewFormat.Matrix: return canConvert('normal');
      case ViewFormat.Tree: return canConvert('extensive');
      case ViewFormat.MAIDDiagram: return canConvert('maid');
      case ViewFormat.Code: return gameFormat === GameFormat.Vegas;
      default: return false;
    }
  };

  const getDisabledReason = (format: ViewFormat) => {
    if (isNative(format)) return undefined;
    switch (format) {
      case ViewFormat.Matrix: return 'Conversion to Normal Form not available';
      case ViewFormat.Tree: return 'Conversion to Extensive Form not available';
      case ViewFormat.MAIDDiagram: return 'Conversion to MAID not available';
      case ViewFormat.Code: return 'Source code only available for Vegas games';
      default: return 'Not available';
    }
  };

  // All 4 model tabs always appear in order: NFG, EFG, MAID, Code
  return [
    {
      format: ViewFormat.Matrix,
      label: 'NFG',
      enabled: isEnabled(ViewFormat.Matrix),
      disabledReason: getDisabledReason(ViewFormat.Matrix),
    },
    {
      format: ViewFormat.Tree,
      label: 'EFG',
      enabled: isEnabled(ViewFormat.Tree),
      disabledReason: getDisabledReason(ViewFormat.Tree),
    },
    {
      format: ViewFormat.MAIDDiagram,
      label: 'MAID',
      enabled: isEnabled(ViewFormat.MAIDDiagram),
      disabledReason: getDisabledReason(ViewFormat.MAIDDiagram),
    },
    {
      format: ViewFormat.Code,
      label: 'Code',
      enabled: isEnabled(ViewFormat.Code),
      disabledReason: getDisabledReason(ViewFormat.Code),
    },
  ];
}

export function MainLayout() {
  const currentGame = useGameStore((s) => s.currentGame);
  const currentGameId = useGameStore((s) => s.currentGameId);
  const games = useGameStore((s) => s.games);

  const viewFormatByGame = useUIStore((s) => s.viewFormatByGame);
  const setViewFormatForGame = useUIStore((s) => s.setViewFormatForGame);

  // Plugin state for compiled code tabs
  const fetchPluginStatus = usePluginStore((s) => s.fetchPluginStatus);
  const compiledCodeByGame = usePluginStore((s) => s.compiledCodeByGame);

  // Track which compiled tab is selected per game (targetId)
  const selectedCompiledTab = useUIStore((s) =>
    currentGameId ? s.viewFormatByGame[`${currentGameId}:compiled`] : null
  );

  // Fetch plugin status on mount
  useEffect(() => {
    void fetchPluginStatus();
  }, [fetchPluginStatus]);

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

  // Get available model tabs
  const modelTabs = useMemo(() => {
    if (!gameFormat) return [];
    return getAvailableTabs(gameFormat, gameSummary?.conversions);
  }, [gameFormat, gameSummary?.conversions]);

  // Get compiled code tabs for the current game
  const compiledTabs: CompiledTab[] = useMemo(() => {
    if (!currentGameId) return [];
    const gameCompiled = compiledCodeByGame[currentGameId];
    if (!gameCompiled) return [];
    return Object.values(gameCompiled).map((c) => ({
      targetId: c.targetId,
      label: c.label,
      language: c.language,
    }));
  }, [currentGameId, compiledCodeByGame]);

  // Get source code for Vegas games
  const gameSourceCode = currentGame && isVegasGame(currentGame) ? currentGame.source_code : null;

  // Callback to select a compiled tab (called from VegasPanel after compilation)
  const handleSelectCompiledTab = useCallback(
    (targetId: string) => {
      if (currentGameId) {
        // Store the compiled tab selection using a special key
        setViewFormatForGame(`${currentGameId}:compiled`, targetId as ViewFormat);
        // Clear the model view selection to indicate we're viewing compiled code
        setViewFormatForGame(currentGameId, 'compiled' as ViewFormat);
      }
    },
    [currentGameId, setViewFormatForGame]
  );

  // Handle model tab click
  const handleModelTabClick = (format: ViewFormat) => {
    if (currentGameId) {
      // Clear compiled tab selection
      setViewFormatForGame(`${currentGameId}:compiled`, null);
      // If clicking the native format, clear the override
      if (gameFormat && format === getNativeViewFormat(gameFormat)) {
        setViewFormatForGame(currentGameId, null);
      } else {
        setViewFormatForGame(currentGameId, format);
      }
    }
  };

  // Handle compiled tab click
  const handleCompiledTabClick = (targetId: string) => {
    if (currentGameId) {
      setViewFormatForGame(`${currentGameId}:compiled`, targetId as ViewFormat);
      setViewFormatForGame(currentGameId, 'compiled' as ViewFormat);
    }
  };

  // Check if we're viewing compiled code
  const isViewingCompiled = activeViewFormat === ('compiled' as ViewFormat) && selectedCompiledTab;

  // Get the compiled code content if viewing compiled
  const compiledContent = useMemo(() => {
    if (!isViewingCompiled || !currentGameId || !selectedCompiledTab) return null;
    const gameCompiled = compiledCodeByGame[currentGameId];
    return gameCompiled?.[selectedCompiledTab as string] ?? null;
  }, [isViewingCompiled, currentGameId, selectedCompiledTab, compiledCodeByGame]);

  // Determine what to render
  const renderContent = () => {
    // Compiled code view
    if (isViewingCompiled && compiledContent) {
      return (
        <ErrorBoundary name="CodeEditor">
          <CodeEditor
            value={compiledContent.content}
            language={compiledContent.language}
            readOnly={true}
          />
        </ErrorBoundary>
      );
    }

    // Native code view (Vegas source)
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
            {/* Model tabs in order: NFG, EFG, MAID, Code */}
            {modelTabs.map((tab) => (
              <button
                key={tab.format}
                className={`view-tab ${!isViewingCompiled && activeViewFormat === tab.format ? 'active' : ''}`}
                onClick={() => handleModelTabClick(tab.format)}
                disabled={!tab.enabled}
                title={tab.enabled ? `View as ${tab.label}` : (tab.disabledReason ?? `Cannot convert to ${tab.label}`)}
              >
                {tab.label}
              </button>
            ))}
            {/* Compiled code tabs stack to the right */}
            {compiledTabs.map((tab) => (
              <button
                key={`compiled-${tab.targetId}`}
                className={`view-tab compiled-tab ${isViewingCompiled && selectedCompiledTab === tab.targetId ? 'active' : ''}`}
                onClick={() => handleCompiledTabClick(tab.targetId)}
                title={`View compiled ${tab.label}`}
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
          <AnalysisPanel onSelectCompiledTab={handleSelectCompiledTab} />
        </ErrorBoundary>
      </aside>
    </main>
  );
}
