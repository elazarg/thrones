import { useGameStore } from '../../stores';
import './Header.css';

export function Header() {
  const game = useGameStore((state) => state.game);
  const loading = useGameStore((state) => state.loading);

  return (
    <header className="header">
      <div className="header-title">
        <strong>{loading ? 'Loading...' : game?.title ?? 'Game Theory Workbench'}</strong>
        {game && <span className="version">{game.version}</span>}
      </div>
      <div className="header-actions">
        <button disabled>Simulate</button>
        <button disabled>LLM</button>
      </div>
    </header>
  );
}
