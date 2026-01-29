import { useEffect } from 'react';
import { ErrorBoundary, ErrorFallback } from '../ErrorBoundary';
import { GameCanvas } from '../canvas/GameCanvas';
import { CodeEditor } from '../editor/CodeEditor';
import { AnalysisPanel } from '../panels/AnalysisPanel';
import { useUIStore, useGameStore } from '../../stores';
import { isVegasGame } from '../../types';
import './MainLayout.css';

export function MainLayout() {
  const editorMode = useUIStore((s) => s.editorMode);
  const setEditorMode = useUIStore((s) => s.setEditorMode);

  // Get current game to check for source_code
  const currentGame = useGameStore((s) => s.currentGame);

  // Vegas games have source_code that can be shown in the editor
  const isVegas = !!(currentGame && isVegasGame(currentGame));
  const gameSourceCode = isVegas ? currentGame.source_code : null;
  const hasSourceCode = !!gameSourceCode;

  // Auto-switch view based on game format:
  // - Vegas games → code view (they're code-based)
  // - Other games → visual view (they're visual)
  useEffect(() => {
    if (isVegas && editorMode !== 'code') {
      setEditorMode('code');
    } else if (!isVegas && editorMode === 'code') {
      setEditorMode('visual');
    }
  }, [currentGame?.id, isVegas, editorMode, setEditorMode]);

  return (
    <main className="main-layout">
      <section className="canvas-section">
        <div className="canvas-toolbar">
          <div className="view-toggle">
            <button
              className={`toggle-btn ${editorMode === 'visual' ? 'active' : ''}`}
              onClick={() => setEditorMode('visual')}
              title="Visual view"
            >
              Visual
            </button>
            <button
              className={`toggle-btn ${editorMode === 'code' ? 'active' : ''}`}
              onClick={() => setEditorMode('code')}
              title={hasSourceCode ? 'View Vegas source code (read-only)' : 'No source code available'}
              disabled={!hasSourceCode}
            >
              Code
            </button>
          </div>
        </div>
        <div className="canvas-content">
          {editorMode === 'visual' ? (
            <ErrorBoundary name="GameCanvas">
              <GameCanvas />
            </ErrorBoundary>
          ) : (
            <ErrorBoundary name="CodeEditor">
              <CodeEditor
                value={gameSourceCode ?? '// No source code available'}
                readOnly={true}
              />
            </ErrorBoundary>
          )}
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
