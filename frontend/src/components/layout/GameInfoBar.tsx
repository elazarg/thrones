import { useGameStore } from '../../stores';
import { isMAIDGame } from '../../types';
import './GameInfoBar.css';

export function GameInfoBar() {
  const currentGame = useGameStore((s) => s.currentGame);

  if (!currentGame) return null;

  // Get players - MAID uses 'agents' instead of 'players'
  const players = isMAIDGame(currentGame) ? currentGame.agents : currentGame.players;

  return (
    <div className="game-info-bar">
      <span className="game-players">Players: {players.join(', ')}</span>
      {currentGame.description && (
        <span className="game-description">{currentGame.description}</span>
      )}
    </div>
  );
}
