import { create } from 'zustand';
import type { ViewMode } from '../canvas';

interface UIStore {
  hoveredNodeId: string | null;
  selectedNodeId: string | null;
  // View mode stored per game - each game has independent view state
  viewModeByGame: Map<string, ViewMode>;
  currentViewMode: ViewMode; // The actual current view mode being rendered
  setHoveredNode: (id: string | null) => void;
  setSelectedNode: (id: string | null) => void;
  // Set view mode for a specific game (null = use native/default view)
  setViewModeForGame: (gameId: string, mode: ViewMode | null) => void;
  // Get view mode override for a specific game (null = use native/default)
  getViewModeForGame: (gameId: string) => ViewMode | null;
  setCurrentViewMode: (mode: ViewMode) => void;
}

export const useUIStore = create<UIStore>((set, get) => ({
  hoveredNodeId: null,
  selectedNodeId: null,
  viewModeByGame: new Map(),
  currentViewMode: 'tree',

  setHoveredNode: (id) => {
    set({ hoveredNodeId: id });
  },

  setSelectedNode: (id) => {
    set({ selectedNodeId: id });
  },

  setViewModeForGame: (gameId, mode) => {
    const newMap = new Map(get().viewModeByGame);
    if (mode === null) {
      newMap.delete(gameId);
    } else {
      newMap.set(gameId, mode);
    }
    set({ viewModeByGame: newMap });
  },

  getViewModeForGame: (gameId) => {
    return get().viewModeByGame.get(gameId) ?? null;
  },

  setCurrentViewMode: (mode) => {
    set({ currentViewMode: mode });
  },
}));
