import { create } from 'zustand';
import type { PluginStatus, CompileTarget, CompiledCode } from '../types';

/** Applicability status for an analysis */
export interface AnalysisApplicability {
  applicable: boolean;
  reason?: string;
  /** True while applicability check is in progress */
  loading?: boolean;
}

interface PluginStore {
  /** Plugin statuses from /api/plugins/status */
  plugins: PluginStatus[];

  /** Analysis applicability per game: gameId -> analysisName -> status */
  applicabilityByGame: Record<string, Record<string, AnalysisApplicability>>;

  /** Games currently being checked for applicability: gameId -> true */
  loadingApplicability: Record<string, boolean>;

  /** Compiled code per game: gameId -> targetId -> CompiledCode */
  compiledCodeByGame: Record<string, Record<string, CompiledCode>>;

  /** Currently compiling target per game */
  compilingByGame: Record<string, string | null>;

  /** Compilation errors per game */
  compileErrorByGame: Record<string, string | null>;

  // Actions
  fetchPluginStatus: () => Promise<void>;
  fetchApplicability: (gameId: string) => Promise<void>;
  isApplicabilityLoading: (gameId: string) => boolean;
  getApplicability: (gameId: string, analysisName: string) => AnalysisApplicability;
  compile: (gameId: string, sourceCode: string, pluginName: string, target: CompileTarget) => Promise<void>;
  clearCompiledCode: (gameId: string, targetId?: string) => void;
  getCompileTargets: () => { pluginName: string; target: CompileTarget }[];
}

export const usePluginStore = create<PluginStore>((set, get) => ({
  plugins: [],
  applicabilityByGame: {},
  loadingApplicability: {},
  compiledCodeByGame: {},
  compilingByGame: {},
  compileErrorByGame: {},

  fetchPluginStatus: async () => {
    try {
      const response = await fetch('/api/plugins/status');
      if (!response.ok) {
        console.error('Failed to fetch plugin status:', response.status);
        return;
      }
      const plugins = await response.json();
      set({ plugins });
    } catch (error) {
      console.error('Failed to fetch plugin status:', error);
    }
  },

  fetchApplicability: async (gameId: string) => {
    // Mark as loading
    set((state) => ({
      loadingApplicability: { ...state.loadingApplicability, [gameId]: true },
    }));

    try {
      const response = await fetch(`/api/plugins/check-applicable/${gameId}`);
      if (!response.ok) {
        console.error('Failed to fetch applicability:', response.status);
        // On error, remove loading state but don't set data (will use fallback)
        set((state) => {
          const { [gameId]: _, ...rest } = state.loadingApplicability;
          return { loadingApplicability: rest };
        });
        return;
      }
      const data = await response.json();
      set((state) => {
        const { [gameId]: _, ...restLoading } = state.loadingApplicability;
        return {
          applicabilityByGame: {
            ...state.applicabilityByGame,
            [gameId]: data.analyses || {},
          },
          loadingApplicability: restLoading,
        };
      });
    } catch (error) {
      console.error('Failed to fetch applicability:', error);
      // On error, remove loading state
      set((state) => {
        const { [gameId]: _, ...rest } = state.loadingApplicability;
        return { loadingApplicability: rest };
      });
    }
  },

  isApplicabilityLoading: (gameId: string) => {
    return !!get().loadingApplicability[gameId];
  },

  getApplicability: (gameId: string, analysisName: string) => {
    const isLoading = !!get().loadingApplicability[gameId];
    const gameApplicability = get().applicabilityByGame[gameId];

    if (isLoading || !gameApplicability) {
      // Still loading or not yet fetched - disable until we know for sure
      return { applicable: false, loading: true, reason: 'Checking...' };
    }
    return gameApplicability[analysisName] || { applicable: true };
  },

  compile: async (gameId, sourceCode, pluginName, target) => {
    // Set compiling state
    set((state) => ({
      compilingByGame: { ...state.compilingByGame, [gameId]: target.id },
      compileErrorByGame: { ...state.compileErrorByGame, [gameId]: null },
    }));

    try {
      const response = await fetch(`/api/compile/${pluginName}/${target.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_code: sourceCode }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Compilation failed' }));
        const errorMessage = errorData?.detail?.error?.message || errorData?.detail || 'Compilation failed';
        throw new Error(errorMessage);
      }

      const result = await response.json();

      // Store compiled code
      const compiled: CompiledCode = {
        targetId: target.id,
        language: result.language || target.language,
        label: target.label,
        content: result.content,
      };

      set((state) => ({
        compiledCodeByGame: {
          ...state.compiledCodeByGame,
          [gameId]: {
            ...state.compiledCodeByGame[gameId],
            [target.id]: compiled,
          },
        },
        compilingByGame: { ...state.compilingByGame, [gameId]: null },
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Compilation failed';
      set((state) => ({
        compilingByGame: { ...state.compilingByGame, [gameId]: null },
        compileErrorByGame: { ...state.compileErrorByGame, [gameId]: message },
      }));
    }
  },

  clearCompiledCode: (gameId, targetId) => {
    if (targetId) {
      set((state) => {
        const gameCode = { ...state.compiledCodeByGame[gameId] };
        delete gameCode[targetId];
        return {
          compiledCodeByGame: {
            ...state.compiledCodeByGame,
            [gameId]: gameCode,
          },
        };
      });
    } else {
      set((state) => {
        const { [gameId]: _, ...rest } = state.compiledCodeByGame;
        return { compiledCodeByGame: rest };
      });
    }
  },

  getCompileTargets: () => {
    const targets: { pluginName: string; target: CompileTarget }[] = [];
    for (const plugin of get().plugins) {
      if (plugin.healthy && plugin.compile_targets) {
        for (const target of plugin.compile_targets) {
          targets.push({ pluginName: plugin.name, target });
        }
      }
    }
    return targets;
  },
}));
