import { useRef, useState } from 'react';
import { useGameStore } from '../../stores';
import './GameSelector.css';

export function GameSelector() {
  const games = useGameStore((state) => state.games);
  const currentGameId = useGameStore((state) => state.currentGameId);
  const currentGame = useGameStore((state) => state.currentGame);
  const selectGame = useGameStore((state) => state.selectGame);
  const uploadGame = useGameStore((state) => state.uploadGame);
  const deleteGame = useGameStore((state) => state.deleteGame);
  const gameLoading = useGameStore((state) => state.gameLoading);

  const [isOpen, setIsOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSelect = async (id: string) => {
    setIsOpen(false);
    await selectGame(id);
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    setIsOpen(false);

    try {
      await uploadGame(file);
    } catch (err) {
      setError(String(err));
    } finally {
      setUploading(false);
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Delete this game?')) {
      await deleteGame(id);
    }
  };

  const displayTitle = gameLoading
    ? 'Loading...'
    : currentGame?.title ?? 'Select Game';

  return (
    <div className="game-selector">
      <button
        className="selector-button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={uploading}
      >
        <span className="selector-title">{displayTitle}</span>
        <span className="selector-arrow">{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && (
        <div className="selector-dropdown">
          {games.map((game) => (
            <div
              key={game.id}
              className={`selector-item ${game.id === currentGameId ? 'selected' : ''}`}
              onClick={() => handleSelect(game.id)}
            >
              <span className="item-title">{game.title}</span>
              <span className="item-players">{game.players.join(', ')}</span>
              {games.length > 1 && (
                <button
                  className="item-delete"
                  onClick={(e) => handleDelete(game.id, e)}
                  title="Delete game"
                >
                  ×
                </button>
              )}
            </div>
          ))}

          <div className="selector-divider" />

          <div className="selector-item upload-item" onClick={handleUploadClick}>
            <span className="upload-icon">+</span>
            <span>Upload Game File...</span>
          </div>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept=".efg,.nfg,.json"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      {uploading && <span className="upload-status">Uploading...</span>}
      {error && <span className="upload-error">{error}</span>}
    </div>
  );
}
