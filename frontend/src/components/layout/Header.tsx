import { useGameStore, useAnalysisStore } from '../../stores';
import { GameSelector } from './GameSelector';
import './Header.css';

export function Header() {
  const reset = useGameStore((state) => state.reset);
  const clearAnalyses = useAnalysisStore((state) => state.clear);

  const handleReset = async () => {
    clearAnalyses();
    await reset();
  };

  return (
    <header className="header">
      <div className="header-left">
        <GameSelector />
      </div>
      <div className="header-actions">
        <button disabled title="Coming soon" aria-label="Simulate (coming soon)">Simulate</button>
        <button disabled title="Coming soon" aria-label="LLM integration (coming soon)">LLM</button>
        <button className="reset-button" onClick={handleReset} title="Clear all games and reset state" aria-label="Reset all games and state">
          Reset
        </button>
      </div>
    </header>
  );
}
