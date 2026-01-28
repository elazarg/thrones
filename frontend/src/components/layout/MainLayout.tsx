import { ErrorBoundary, ErrorFallback } from '../ErrorBoundary';
import { GameCanvas } from '../canvas/GameCanvas';
import { AnalysisPanel } from '../panels/AnalysisPanel';
import './MainLayout.css';

export function MainLayout() {
  return (
    <main className="main-layout">
      <section className="canvas-section">
        <ErrorBoundary name="GameCanvas">
          <GameCanvas />
        </ErrorBoundary>
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
