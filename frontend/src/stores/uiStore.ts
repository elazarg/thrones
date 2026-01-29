import { create } from 'zustand';
import type { ViewMode } from '../canvas';

/** Editor mode: visual canvas or code editor */
export type EditorMode = 'visual' | 'code';

interface UIStore {
  hoveredNodeId: string | null;
  selectedNodeId: string | null;
  // View mode stored per game - each game has independent view state
  // Using Record instead of Map for JSON serializability
  viewModeByGame: Record<string, ViewMode>;
  currentViewMode: ViewMode; // The actual current view mode being rendered
  // Editor mode: visual (canvas) or code (Monaco)
  editorMode: EditorMode;
  // Source code for the current game (if available)
  sourceCode: string | null;
  // Config modal state
  isConfigOpen: boolean;
  setHoveredNode: (id: string | null) => void;
  setSelectedNode: (id: string | null) => void;
  // Set view mode for a specific game (null = use native/default view)
  setViewModeForGame: (gameId: string, mode: ViewMode | null) => void;
  // Get view mode override for a specific game (null = use native/default)
  getViewModeForGame: (gameId: string) => ViewMode | null;
  setCurrentViewMode: (mode: ViewMode) => void;
  setEditorMode: (mode: EditorMode) => void;
  setSourceCode: (code: string | null) => void;
  openConfig: () => void;
  closeConfig: () => void;
}

export const useUIStore = create<UIStore>((set, get) => ({
  hoveredNodeId: null,
  selectedNodeId: null,
  viewModeByGame: {},
  currentViewMode: 'tree',
  editorMode: 'visual',
  sourceCode: null,
  isConfigOpen: false,

  setHoveredNode: (id) => {
    set({ hoveredNodeId: id });
  },

  setSelectedNode: (id) => {
    set({ selectedNodeId: id });
  },

  setViewModeForGame: (gameId, mode) => {
    const current = get().viewModeByGame;
    if (mode === null) {
      // Remove the key by spreading without it
      const { [gameId]: _, ...rest } = current;
      set({ viewModeByGame: rest });
    } else {
      set({ viewModeByGame: { ...current, [gameId]: mode } });
    }
  },

  getViewModeForGame: (gameId) => {
    return get().viewModeByGame[gameId] ?? null;
  },

  setCurrentViewMode: (mode) => {
    set({ currentViewMode: mode });
  },

  setEditorMode: (mode) => {
    set({ editorMode: mode });
  },

  setSourceCode: (code) => {
    set({ sourceCode: code });
  },

  openConfig: () => {
    set({ isConfigOpen: true });
  },

  closeConfig: () => {
    set({ isConfigOpen: false });
  },
}));
