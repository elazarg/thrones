import { create } from 'zustand';
import type { AnalysisResult } from '../types';

interface AnalysisStore {
  results: AnalysisResult[];
  loading: boolean;
  error: string | null;
  selectedEquilibriumIndex: number | null;
  fetchAnalyses: (gameId: string) => Promise<void>;
  selectEquilibrium: (index: number | null) => void;
  clear: () => void;
}

export const useAnalysisStore = create<AnalysisStore>((set) => ({
  results: [],
  loading: false,
  error: null,
  selectedEquilibriumIndex: null,

  fetchAnalyses: async (gameId: string) => {
    set({ loading: true, error: null });
    try {
      const response = await fetch(`/api/games/${gameId}/analyses`);
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const results = await response.json();
      set({ results, loading: false, selectedEquilibriumIndex: null });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  selectEquilibrium: (index) => {
    set({ selectedEquilibriumIndex: index });
  },

  clear: () => {
    set({ results: [], selectedEquilibriumIndex: null, error: null });
  },
}));
