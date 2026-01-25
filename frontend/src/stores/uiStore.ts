import { create } from 'zustand';
import type { ViewMode } from '../canvas';

interface UIStore {
  hoveredNodeId: string | null;
  selectedNodeId: string | null;
  viewModeOverride: ViewMode | null; // null = auto-detect, 'tree' or 'matrix' = forced
  currentViewMode: ViewMode; // The actual current view mode
  setHoveredNode: (id: string | null) => void;
  setSelectedNode: (id: string | null) => void;
  setViewMode: (mode: ViewMode | null) => void;
  setCurrentViewMode: (mode: ViewMode) => void;
  toggleViewMode: (currentMode: ViewMode, canToggle: boolean) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  hoveredNodeId: null,
  selectedNodeId: null,
  viewModeOverride: null,
  currentViewMode: 'tree',

  setHoveredNode: (id) => {
    set({ hoveredNodeId: id });
  },

  setSelectedNode: (id) => {
    set({ selectedNodeId: id });
  },

  setViewMode: (mode) => {
    set({ viewModeOverride: mode });
  },

  setCurrentViewMode: (mode) => {
    set({ currentViewMode: mode });
  },

  toggleViewMode: (currentMode, canToggle) => {
    if (!canToggle) return;
    set({ viewModeOverride: currentMode === 'tree' ? 'matrix' : 'tree' });
  },
}));
