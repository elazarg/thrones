import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type SolverType = 'exhaustive' | 'quick' | 'pure' | 'approximate';

interface ConfigState {
  // Analysis defaults
  defaultSolver: SolverType;
  defaultMaxEquilibria: number;
  analysisTimeout: number;

  // Visual preferences
  zoomSpeed: number;

  // Actions
  setDefaultSolver: (solver: SolverType) => void;
  setDefaultMaxEquilibria: (max: number) => void;
  setAnalysisTimeout: (timeout: number) => void;
  setZoomSpeed: (speed: number) => void;
  resetToDefaults: () => void;
}

const defaults = {
  defaultSolver: 'quick' as SolverType,
  defaultMaxEquilibria: 1,
  analysisTimeout: 60,
  zoomSpeed: 0.15,
};

export const useConfigStore = create<ConfigState>()(
  persist(
    (set) => ({
      ...defaults,
      setDefaultSolver: (solver) => set({ defaultSolver: solver }),
      setDefaultMaxEquilibria: (max) => set({ defaultMaxEquilibria: max }),
      setAnalysisTimeout: (timeout) => set({ analysisTimeout: timeout }),
      setZoomSpeed: (speed) => set({ zoomSpeed: speed }),
      resetToDefaults: () => set(defaults),
    }),
    {
      name: 'thrones-config',
      version: 1,
      // Merge ensures new fields from defaults are included when upgrading
      merge: (persisted, current) => ({
        ...current,
        ...defaults,
        ...(persisted as Partial<ConfigState>),
      }),
    }
  )
);
