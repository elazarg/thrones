import { create } from 'zustand';
import type { GameSummary, AnyGame } from '../types';
import { parseErrorResponse } from '../lib/api';

interface GameStore {
  // All available games
  games: GameSummary[];
  gamesLoading: boolean;
  gamesError: string | null;

  // Currently selected game (can be extensive or normal form)
  currentGameId: string | null;
  currentGame: AnyGame | null;
  gameLoading: boolean;
  gameError: string | null;

  // Conversion cache: gameId-format -> game
  conversionCache: Map<string, AnyGame>;

  // Actions
  fetchGames: () => Promise<void>;
  selectGame: (id: string) => Promise<void>;
  uploadGame: (file: File) => Promise<AnyGame>;
  deleteGame: (id: string) => Promise<void>;
  reset: () => Promise<void>;
  fetchConverted: (gameId: string, format: 'extensive' | 'normal') => Promise<AnyGame | null>;
}

export const useGameStore = create<GameStore>((set, get) => ({
  games: [],
  gamesLoading: false,
  gamesError: null,

  currentGameId: null,
  currentGame: null,
  gameLoading: false,
  gameError: null,

  conversionCache: new Map(),

  fetchGames: async () => {
    set({ gamesLoading: true, gamesError: null });
    try {
      const response = await fetch('/api/games');
      if (!response.ok) {
        throw new Error(await parseErrorResponse(response));
      }
      const games = await response.json();
      set({ games, gamesLoading: false });

      // Auto-select first game if none selected
      const state = get();
      if (!state.currentGameId && games.length > 0) {
        get().selectGame(games[0].id);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      set({ gamesError: message, gamesLoading: false });
    }
  },

  selectGame: async (id: string) => {
    set({ gameLoading: true, gameError: null, currentGameId: id });
    try {
      const response = await fetch(`/api/games/${id}`);
      if (!response.ok) {
        throw new Error(await parseErrorResponse(response));
      }
      const game = await response.json();
      set({ currentGame: game, gameLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      set({ gameError: message, gameLoading: false });
    }
  },

  uploadGame: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/games/upload', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await parseErrorResponse(response));
    }

    const game = await response.json();

    // Refresh games list and select the new game
    await get().fetchGames();
    await get().selectGame(game.id);

    return game;
  },

  deleteGame: async (id: string) => {
    const response = await fetch(`/api/games/${id}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(await parseErrorResponse(response));
    }

    // Refresh games list
    await get().fetchGames();

    // If deleted game was selected, select another
    const state = get();
    if (state.currentGameId === id) {
      const remaining = state.games.filter((g) => g.id !== id);
      if (remaining.length > 0) {
        await get().selectGame(remaining[0].id);
      } else {
        set({ currentGameId: null, currentGame: null });
      }
    }
  },

  reset: async () => {
    console.log('[GameStore] Resetting state...');
    try {
      const response = await fetch('/api/reset', { method: 'POST' });
      if (!response.ok) {
        throw new Error(await parseErrorResponse(response));
      }
      const result = await response.json();
      console.log('[GameStore] Reset complete:', result);

      // Clear local state and refresh
      set({ currentGameId: null, currentGame: null, conversionCache: new Map() });
      await get().fetchGames();
    } catch (err) {
      console.error('[GameStore] Reset failed:', err);
      throw err;
    }
  },

  fetchConverted: async (gameId: string, format: 'extensive' | 'normal') => {
    const cacheKey = `${gameId}-${format}`;
    const cached = get().conversionCache.get(cacheKey);
    if (cached) {
      return cached;
    }

    try {
      const response = await fetch(`/api/games/${gameId}/as/${format}`);
      if (!response.ok) {
        console.warn(`[GameStore] Conversion failed: ${await response.text()}`);
        return null;
      }
      const game = await response.json();

      // Update cache
      const newCache = new Map(get().conversionCache);
      newCache.set(cacheKey, game);
      set({ conversionCache: newCache });

      return game;
    } catch (err) {
      console.error('[GameStore] Conversion fetch failed:', err);
      return null;
    }
  },
}));
