import { create } from 'zustand';
import type { AnalysisResult } from '../types';

/** Options for running analysis */
export interface AnalysisOptions {
  solver?: 'exhaustive' | 'quick' | 'pure' | 'approximate';
  maxEquilibria?: number;
}

interface AnalysisStore {
  /** Cached results per analysis type */
  resultsByType: Record<string, AnalysisResult | null>;
  /** Which analysis is currently loading */
  loadingAnalysis: string | null;
  error: string | null;
  selectedEquilibriumIndex: number | null;
  selectedAnalysisId: string | null;
  abortController: AbortController | null;
  runAnalysis: (gameId: string, analysisId: string, options?: AnalysisOptions) => Promise<void>;
  cancelAnalysis: () => void;
  selectEquilibrium: (analysisId: string, index: number | null) => void;
  clear: () => void;
  getResult: (analysisId: string) => AnalysisResult | null;
  isLoading: (analysisId: string) => boolean;
}

export const useAnalysisStore = create<AnalysisStore>((set, get) => ({
  resultsByType: {},
  loadingAnalysis: null,
  error: null,
  selectedEquilibriumIndex: null,
  selectedAnalysisId: null,
  abortController: null,

  runAnalysis: async (gameId: string, analysisId: string, options?: AnalysisOptions) => {
    // Cancel any existing request
    const existing = get().abortController;
    if (existing) {
      console.log('[Analysis] Cancelling previous request');
      existing.abort();
    }

    const controller = new AbortController();
    set({ loadingAnalysis: analysisId, error: null, abortController: controller });
    console.log(`[Analysis] Starting ${analysisId} for game ${gameId}`, options);

    try {
      // Build URL with query params
      const params = new URLSearchParams();
      if (options?.solver) {
        params.set('solver', options.solver);
      }
      if (options?.maxEquilibria) {
        params.set('max_equilibria', String(options.maxEquilibria));
      }
      const queryString = params.toString();
      const url = `/api/games/${gameId}/analyses${queryString ? '?' + queryString : ''}`;

      const response = await fetch(url, {
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const results: AnalysisResult[] = await response.json();
      console.log(`[Analysis] Completed ${analysisId}: ${results.length} results`);

      // Find relevant result based on analysis type
      let relevantResult: AnalysisResult | null = null;

      if (analysisId === 'iesds') {
        // IESDS: look for eliminated/surviving
        relevantResult = results.find(r => r.details.eliminated !== undefined) || null;
      } else {
        // Default: equilibria results for Nash/Pure/Approx
        relevantResult = results.find(r => r.details.equilibria) || results[0] || null;
      }

      set((state) => ({
        resultsByType: {
          ...state.resultsByType,
          [analysisId]: relevantResult,
        },
        loadingAnalysis: null,
        selectedEquilibriumIndex: null,
        selectedAnalysisId: relevantResult?.details.equilibria ? analysisId : state.selectedAnalysisId,
        abortController: null,
      }));
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        console.log('[Analysis] Cancelled by user');
        set({ loadingAnalysis: null, abortController: null });
      } else {
        console.error('[Analysis] Failed:', err);
        set({ error: String(err), loadingAnalysis: null, abortController: null });
      }
    }
  },

  cancelAnalysis: () => {
    const controller = get().abortController;
    if (controller) {
      console.log('[Analysis] Cancelling...');
      controller.abort();
      set({ loadingAnalysis: null, abortController: null });
    }
  },

  selectEquilibrium: (analysisId: string, index: number | null) => {
    set({ selectedAnalysisId: analysisId, selectedEquilibriumIndex: index });
  },

  clear: () => {
    // Cancel any in-flight request when clearing
    const controller = get().abortController;
    if (controller) {
      controller.abort();
    }
    set({
      resultsByType: {},
      selectedEquilibriumIndex: null,
      selectedAnalysisId: null,
      error: null,
      loadingAnalysis: null,
      abortController: null,
    });
  },

  getResult: (analysisId: string) => {
    return get().resultsByType[analysisId] || null;
  },

  isLoading: (analysisId: string) => {
    return get().loadingAnalysis === analysisId;
  },
}));
