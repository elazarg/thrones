import { create } from 'zustand';
import type { AnalysisResult, Task } from '../types';
import { parseErrorResponse } from '../lib/api';
import { logger } from '../lib/logger';

/** Options for running analysis */
export interface AnalysisOptions {
  solver?: 'exhaustive' | 'quick' | 'pure' | 'approximate';
  maxEquilibria?: number;
}

/** Map analysis UI ID to plugin name */
const PLUGIN_NAMES: Record<string, string> = {
  nash: 'Nash Equilibrium',
  'pure-ne': 'Nash Equilibrium',
  'approx-ne': 'Nash Equilibrium',
  iesds: 'IESDS',
  'maid-nash': 'MAID Nash Equilibrium',
};

/** Polling interval in milliseconds */
const POLL_INTERVAL_MS = 500;

/** Generate a unique client ID for task ownership */
function generateClientId(): string {
  const stored = sessionStorage.getItem('analysis-client-id');
  if (stored) return stored;
  const id = `client-${Math.random().toString(36).slice(2, 10)}`;
  sessionStorage.setItem('analysis-client-id', id);
  return id;
}

interface AnalysisStore {
  /** Cached results per analysis type */
  resultsByType: Record<string, AnalysisResult | null>;
  /** Which analysis is currently loading */
  loadingAnalysis: string | null;
  error: string | null;
  selectedEquilibriumIndex: number | null;
  selectedAnalysisId: string | null;
  /** Whether IESDS overlay is active */
  isIESDSSelected: boolean;
  /** Current task ID (for cancellation) */
  currentTaskId: string | null;
  /** Client ID for task ownership */
  clientId: string;
  runAnalysis: (gameId: string, analysisId: string, options?: AnalysisOptions) => Promise<void>;
  cancelAnalysis: () => void;
  selectEquilibrium: (analysisId: string, index: number | null) => void;
  selectIESDS: (selected: boolean) => void;
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
  isIESDSSelected: false,
  currentTaskId: null,
  clientId: generateClientId(),

  runAnalysis: async (gameId: string, analysisId: string, options?: AnalysisOptions) => {
    // Cancel any existing task
    const existing = get().currentTaskId;
    if (existing) {
      logger.debug('Cancelling previous task:', existing);
      try {
        await fetch(`/api/tasks/${existing}`, { method: 'DELETE' });
      } catch {
        // Ignore cancellation errors
      }
    }

    set({ loadingAnalysis: analysisId, error: null, currentTaskId: null });

    // Map analysis ID to plugin name
    const pluginName = PLUGIN_NAMES[analysisId] || analysisId;
    logger.info(`Starting ${analysisId} (plugin: ${pluginName}) for game ${gameId}`, options);

    try {
      // Build query params for task submission
      const params = new URLSearchParams();
      params.set('game_id', gameId);
      params.set('plugin', pluginName);
      params.set('owner', get().clientId);
      if (options?.solver) {
        params.set('solver', options.solver);
      }
      if (options?.maxEquilibria) {
        params.set('max_equilibria', String(options.maxEquilibria));
      }

      // Submit task
      const submitResponse = await fetch(`/api/tasks?${params.toString()}`, {
        method: 'POST',
      });
      if (!submitResponse.ok) {
        throw new Error(await parseErrorResponse(submitResponse));
      }
      const taskInfo = await submitResponse.json();
      const taskId = taskInfo.task_id;
      logger.debug(`Task submitted: ${taskId}`);

      set({ currentTaskId: taskId });

      // Poll for completion
      let task: Task;
      while (true) {
        // Check if we've been cancelled (currentTaskId cleared)
        if (get().currentTaskId !== taskId) {
          logger.debug('Task polling stopped (different task or cleared)');
          return;
        }

        const pollResponse = await fetch(`/api/tasks/${taskId}`);
        if (!pollResponse.ok) {
          throw new Error(await parseErrorResponse(pollResponse));
        }
        task = await pollResponse.json();

        if (task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') {
          break;
        }

        // Wait before next poll
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      }

      // Handle result
      if (task.status === 'failed') {
        throw new Error(task.error || 'Analysis failed');
      }

      if (task.status === 'cancelled') {
        logger.debug('Task was cancelled');
        set({ loadingAnalysis: null, currentTaskId: null });
        return;
      }

      // Task completed successfully
      const result = task.result;
      logger.info(`Completed ${analysisId}:`, result?.summary);

      // Find relevant result based on analysis type
      let relevantResult: AnalysisResult | null = result;

      // If this is IESDS, verify we got IESDS data
      if (analysisId === 'iesds' && result && result.details.eliminated === undefined) {
        relevantResult = null;
      }

      // If this is Nash/Pure/Approx, verify we got equilibria data
      if (analysisId !== 'iesds' && result && !result.details.equilibria && !result.details.error) {
        relevantResult = null;
      }

      set((state) => ({
        resultsByType: {
          ...state.resultsByType,
          [analysisId]: relevantResult,
        },
        loadingAnalysis: null,
        selectedEquilibriumIndex: null,
        selectedAnalysisId: relevantResult?.details.equilibria ? analysisId : state.selectedAnalysisId,
        currentTaskId: null,
      }));
    } catch (err) {
      logger.error('Analysis failed:', err);
      const message = err instanceof Error ? err.message : String(err);
      set({ error: message, loadingAnalysis: null, currentTaskId: null });
    }
  },

  cancelAnalysis: () => {
    const taskId = get().currentTaskId;
    if (taskId) {
      logger.debug('Cancelling task:', taskId);
      // Fire and forget - don't await
      fetch(`/api/tasks/${taskId}`, { method: 'DELETE' }).catch(() => {
        // Ignore errors
      });
      set({ loadingAnalysis: null, currentTaskId: null });
    }
  },

  selectEquilibrium: (analysisId: string, index: number | null) => {
    set({ selectedAnalysisId: analysisId, selectedEquilibriumIndex: index, isIESDSSelected: false });
  },

  selectIESDS: (selected: boolean) => {
    set({
      isIESDSSelected: selected,
      // Clear equilibrium selection when IESDS is selected
      selectedEquilibriumIndex: selected ? null : get().selectedEquilibriumIndex,
      selectedAnalysisId: selected ? null : get().selectedAnalysisId,
    });
  },

  clear: () => {
    // Cancel any in-flight task when clearing
    const taskId = get().currentTaskId;
    if (taskId) {
      fetch(`/api/tasks/${taskId}`, { method: 'DELETE' }).catch(() => {
        // Ignore errors
      });
    }
    set({
      resultsByType: {},
      selectedEquilibriumIndex: null,
      selectedAnalysisId: null,
      isIESDSSelected: false,
      error: null,
      loadingAnalysis: null,
      currentTaskId: null,
    });
  },

  getResult: (analysisId: string) => {
    return get().resultsByType[analysisId] || null;
  },

  isLoading: (analysisId: string) => {
    return get().loadingAnalysis === analysisId;
  },
}));
