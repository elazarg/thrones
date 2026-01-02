import { useGameStore, useAnalysisStore } from '../../stores';
import { GameSelector } from './GameSelector';
import './Header.css';

export function Header() {
  const currentGame = useGameStore((state) => state.currentGame);
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
        {currentGame && (
          <span className="version-badge">{currentGame.version}</span>
        )}
      </div>
      <div className="header-actions">
        <button disabled title="Coming soon">Simulate</button>
        <button disabled title="Coming soon">LLM</button>
        <button className="reset-button" onClick={handleReset} title="Clear all games and reset state">
          Reset
        </button>
      </div>
    </header>
  );
}
