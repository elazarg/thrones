import { GameCanvas } from '../canvas/GameCanvas';
import { AnalysisPanel } from '../panels/AnalysisPanel';
import './MainLayout.css';

export function MainLayout() {
  return (
    <main className="main-layout">
      <section className="canvas-section">
        <GameCanvas />
      </section>
      <aside className="panel-section">
        <AnalysisPanel />
      </aside>
    </main>
  );
}
