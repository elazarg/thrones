import { useRef, useState } from 'react';
import { useGameStore } from '../../stores';
import './GameSelector.css';

/** Maximum file size in bytes (5 MB) */
const MAX_FILE_SIZE = 5 * 1024 * 1024;

/** Allowed file extensions */
const ALLOWED_EXTENSIONS = ['.efg', '.nfg', '.json'];

/**
 * Validate a file before upload.
 * Returns null if valid, or an error message string if invalid.
 */
function validateFile(file: File): string | null {
  // Check file size
  if (file.size > MAX_FILE_SIZE) {
    const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
    return `File too large (${sizeMB} MB). Maximum size is 5 MB.`;
  }

  // Check file extension
  const fileName = file.name.toLowerCase();
  const hasValidExtension = ALLOWED_EXTENSIONS.some((ext) => fileName.endsWith(ext));
  if (!hasValidExtension) {
    return `Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`;
  }

  return null;
}

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

    // Validate file before upload
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      return;
    }

    setUploading(true);
    setError(null);
    setIsOpen(false);

    try {
      await uploadGame(file);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
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
              <span className="item-meta">
                {game.format === 'maid' && <span className="format-badge maid">MAID</span>}
                <span className="item-players">{game.players.join(', ')}</span>
              </span>
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

          <button type="button" className="selector-item upload-item" onClick={handleUploadClick}>
            <span className="upload-icon">+</span>
            <span>Upload Game File...</span>
          </button>
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
