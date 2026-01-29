import { create } from 'zustand';
import { ViewFormat } from '../types';

interface UIStore {
  hoveredNodeId: string | null;
  selectedNodeId: string | null;

  /**
   * Selected view format per game.
   * Each game independently tracks which view the user wants to see.
   * null = use the native view for that game's format.
   */
  viewFormatByGame: Record<string, ViewFormat>;

  /**
   * The actual view format currently being rendered.
   * Updated by the canvas/editor components after they determine what to show.
   */
  currentViewFormat: ViewFormat;

  // Config modal state
  isConfigOpen: boolean;

  // Actions
  setHoveredNode: (id: string | null) => void;
  setSelectedNode: (id: string | null) => void;

  /**
   * Set the view format for a specific game.
   * Pass null to reset to native view.
   */
  setViewFormatForGame: (gameId: string, format: ViewFormat | null) => void;

  /**
   * Get the selected view format for a game.
   * Returns null if using native view.
   */
  getViewFormatForGame: (gameId: string) => ViewFormat | null;

  /**
   * Update the current view format being rendered.
   * Called by canvas/editor components.
   */
  setCurrentViewFormat: (format: ViewFormat) => void;

  openConfig: () => void;
  closeConfig: () => void;
}

export const useUIStore = create<UIStore>((set, get) => ({
  hoveredNodeId: null,
  selectedNodeId: null,
  viewFormatByGame: {},
  currentViewFormat: ViewFormat.Tree,
  isConfigOpen: false,

  setHoveredNode: (id) => {
    set({ hoveredNodeId: id });
  },

  setSelectedNode: (id) => {
    set({ selectedNodeId: id });
  },

  setViewFormatForGame: (gameId, format) => {
    const current = get().viewFormatByGame;
    if (format === null) {
      // Remove the override - use native view
      const { [gameId]: _, ...rest } = current;
      set({ viewFormatByGame: rest });
    } else {
      set({ viewFormatByGame: { ...current, [gameId]: format } });
    }
  },

  getViewFormatForGame: (gameId) => {
    return get().viewFormatByGame[gameId] ?? null;
  },

  setCurrentViewFormat: (format) => {
    set({ currentViewFormat: format });
  },

  openConfig: () => {
    set({ isConfigOpen: true });
  },

  closeConfig: () => {
    set({ isConfigOpen: false });
  },
}));
