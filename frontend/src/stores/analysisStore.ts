import { create } from 'zustand';
import type { AnalysisResult } from '../types';

interface AnalysisStore {
  results: AnalysisResult[];
  loading: boolean;
  error: string | null;
  selectedEquilibriumIndex: number | null;
  fetchAnalyses: () => Promise<void>;
  selectEquilibrium: (index: number | null) => void;
}

export const useAnalysisStore = create<AnalysisStore>((set) => ({
  results: [],
  loading: false,
  error: null,
  selectedEquilibriumIndex: null,

  fetchAnalyses: async () => {
    set({ loading: true, error: null });
    try {
      const response = await fetch('/api/analyses');
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const results = await response.json();
      set({ results, loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  selectEquilibrium: (index) => {
    set({ selectedEquilibriumIndex: index });
  },
}));
