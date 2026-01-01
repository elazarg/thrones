import { create } from 'zustand';

interface UIStore {
  hoveredNodeId: string | null;
  selectedNodeId: string | null;
  setHoveredNode: (id: string | null) => void;
  setSelectedNode: (id: string | null) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  hoveredNodeId: null,
  selectedNodeId: null,

  setHoveredNode: (id) => {
    set({ hoveredNodeId: id });
  },

  setSelectedNode: (id) => {
    set({ selectedNodeId: id });
  },
}));
