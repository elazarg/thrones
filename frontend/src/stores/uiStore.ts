import { create } from 'zustand';
import type { ViewMode } from '../canvas';

interface UIStore {
  hoveredNodeId: string | null;
  selectedNodeId: string | null;
  viewModeOverride: ViewMode | null; // null = auto-detect, 'tree' or 'matrix' = forced
  setHoveredNode: (id: string | null) => void;
  setSelectedNode: (id: string | null) => void;
  setViewMode: (mode: ViewMode | null) => void;
  toggleViewMode: (currentMode: ViewMode, canToggle: boolean) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  hoveredNodeId: null,
  selectedNodeId: null,
  viewModeOverride: null,

  setHoveredNode: (id) => {
    set({ hoveredNodeId: id });
  },

  setSelectedNode: (id) => {
    set({ selectedNodeId: id });
  },

  setViewMode: (mode) => {
    set({ viewModeOverride: mode });
  },

  toggleViewMode: (currentMode, canToggle) => {
    if (!canToggle) return;
    set({ viewModeOverride: currentMode === 'tree' ? 'matrix' : 'tree' });
  },
}));
