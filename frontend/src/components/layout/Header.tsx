import { useGameStore } from '../../stores';
import { GameSelector } from './GameSelector';
import './Header.css';

export function Header() {
  const currentGame = useGameStore((state) => state.currentGame);

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
      </div>
    </header>
  );
}
