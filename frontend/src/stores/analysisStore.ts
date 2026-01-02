import { create } from 'zustand';
import type { AnalysisResult } from '../types';

interface AnalysisStore {
  results: AnalysisResult[];
  loading: boolean;
  error: string | null;
  selectedEquilibriumIndex: number | null;
  abortController: AbortController | null;
  runAnalysis: (gameId: string) => Promise<void>;
  cancelAnalysis: () => void;
  selectEquilibrium: (index: number | null) => void;
  clear: () => void;
}

export const useAnalysisStore = create<AnalysisStore>((set, get) => ({
  results: [],
  loading: false,
  error: null,
  selectedEquilibriumIndex: null,
  abortController: null,

  runAnalysis: async (gameId: string) => {
    // Cancel any existing request
    const existing = get().abortController;
    if (existing) {
      console.log('[Analysis] Cancelling previous request');
      existing.abort();
    }

    const controller = new AbortController();
    set({ loading: true, error: null, abortController: controller });
    console.log(`[Analysis] Starting for game ${gameId}`);

    try {
      const response = await fetch(`/api/games/${gameId}/analyses`, {
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const results = await response.json();
      console.log(`[Analysis] Completed: ${results.length} results`);
      set({ results, loading: false, selectedEquilibriumIndex: null, abortController: null });
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        console.log('[Analysis] Cancelled by user');
        // Don't set error state for user-initiated cancellation
        set({ loading: false, abortController: null });
      } else {
        console.error('[Analysis] Failed:', err);
        set({ error: String(err), loading: false, abortController: null });
      }
    }
  },

  cancelAnalysis: () => {
    const controller = get().abortController;
    if (controller) {
      console.log('[Analysis] Cancelling...');
      controller.abort();
      set({ loading: false, abortController: null });
    }
  },

  selectEquilibrium: (index) => {
    set({ selectedEquilibriumIndex: index });
  },

  clear: () => {
    // Cancel any in-flight request when clearing
    const controller = get().abortController;
    if (controller) {
      controller.abort();
    }
    set({ results: [], selectedEquilibriumIndex: null, error: null, loading: false, abortController: null });
  },
}));
