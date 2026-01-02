import { create } from 'zustand';
import type { Game, GameSummary } from '../types';

interface GameStore {
  // All available games
  games: GameSummary[];
  gamesLoading: boolean;
  gamesError: string | null;

  // Currently selected game
  currentGameId: string | null;
  currentGame: Game | null;
  gameLoading: boolean;
  gameError: string | null;

  // Actions
  fetchGames: () => Promise<void>;
  selectGame: (id: string) => Promise<void>;
  uploadGame: (file: File) => Promise<Game>;
  deleteGame: (id: string) => Promise<void>;
  reset: () => Promise<void>;
}

export const useGameStore = create<GameStore>((set, get) => ({
  games: [],
  gamesLoading: false,
  gamesError: null,

  currentGameId: null,
  currentGame: null,
  gameLoading: false,
  gameError: null,

  fetchGames: async () => {
    set({ gamesLoading: true, gamesError: null });
    try {
      const response = await fetch('/api/games');
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const games = await response.json();
      set({ games, gamesLoading: false });

      // Auto-select first game if none selected
      const state = get();
      if (!state.currentGameId && games.length > 0) {
        get().selectGame(games[0].id);
      }
    } catch (err) {
      set({ gamesError: String(err), gamesLoading: false });
    }
  },

  selectGame: async (id: string) => {
    set({ gameLoading: true, gameError: null, currentGameId: id });
    try {
      const response = await fetch(`/api/games/${id}`);
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const game = await response.json();
      set({ currentGame: game, gameLoading: false });
    } catch (err) {
      set({ gameError: String(err), gameLoading: false });
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
      const error = await response.text();
      throw new Error(error);
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
      throw new Error(await response.text());
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
        throw new Error(await response.text());
      }
      const result = await response.json();
      console.log('[GameStore] Reset complete:', result);

      // Clear local state and refresh
      set({ currentGameId: null, currentGame: null });
      await get().fetchGames();
    } catch (err) {
      console.error('[GameStore] Reset failed:', err);
      throw err;
    }
  },
}));
