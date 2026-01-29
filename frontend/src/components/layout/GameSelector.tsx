import { useRef, useState, useMemo } from 'react';
import { useGameStore } from '../../stores';
import type { GameSummary } from '../../types';
import './GameSelector.css';

/** Maximum file size in bytes (5 MB) */
const MAX_FILE_SIZE = 5 * 1024 * 1024;

/** Allowed file extensions */
const ALLOWED_EXTENSIONS = ['.efg', '.nfg', '.json'];

/** Format display order and labels */
const FORMAT_ORDER: Record<string, number> = { extensive: 0, normal: 1, maid: 2 };
const FORMAT_LABELS: Record<string, string> = { extensive: 'EFG', normal: 'NFG', maid: 'MAID' };

/** Sort games by format, then by title */
function sortGames(games: GameSummary[]): GameSummary[] {
  return [...games].sort((a, b) => {
    const formatDiff = (FORMAT_ORDER[a.format] ?? 99) - (FORMAT_ORDER[b.format] ?? 99);
    if (formatDiff !== 0) return formatDiff;
    return a.title.localeCompare(b.title);
  });
}

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
  const [hoveredGameId, setHoveredGameId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sort games by format, then by title
  const sortedGames = useMemo(() => sortGames(games), [games]);

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
          {sortedGames.map((game) => (
            <div
              key={game.id}
              className={`selector-item ${game.id === currentGameId ? 'selected' : ''}`}
              onClick={() => handleSelect(game.id)}
              onMouseEnter={() => setHoveredGameId(game.id)}
              onMouseLeave={() => setHoveredGameId(null)}
            >
              <span className={`format-badge ${game.format}`}>
                {FORMAT_LABELS[game.format] ?? game.format.toUpperCase()}
              </span>
              <span className="item-title">{game.title}</span>
              {sortedGames.length > 1 && (
                <button
                  className="item-delete"
                  onClick={(e) => handleDelete(game.id, e)}
                  title="Delete game"
                >
                  ×
                </button>
              )}
              {hoveredGameId === game.id && (
                <div className="game-tooltip">
                  {game.description && (
                    <div className="tooltip-description">{game.description}</div>
                  )}
                  <div className="tooltip-row">
                    <span className="tooltip-label">Players:</span>
                    <span className="tooltip-value">{game.players.join(', ')}</span>
                  </div>
                  <div className="tooltip-row">
                    <span className="tooltip-label">Format:</span>
                    <span className="tooltip-value">{game.format}</span>
                  </div>
                  {game.tags && game.tags.length > 0 && (
                    <div className="tooltip-tags">
                      {game.tags.map((tag) => (
                        <span key={tag} className="tooltip-tag">#{tag}</span>
                      ))}
                    </div>
                  )}
                </div>
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
