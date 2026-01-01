import { create } from 'zustand';
import type { Game } from '../types';

interface GameStore {
  game: Game | null;
  loading: boolean;
  error: string | null;
  fetchGame: () => Promise<void>;
}

export const useGameStore = create<GameStore>((set) => ({
  game: null,
  loading: false,
  error: null,

  fetchGame: async () => {
    set({ loading: true, error: null });
    try {
      const response = await fetch('/api/game');
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const game = await response.json();
      set({ game, loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },
}));
