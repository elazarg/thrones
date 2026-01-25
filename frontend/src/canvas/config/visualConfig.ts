/**
 * Centralized visual configuration for the game canvas.
 * All magic numbers and visual constants should be defined here.
 */

export const visualConfig = {
  // Node rendering
  node: {
    decisionRadius: 20,
    outcomeSize: 16,
    strokeWidth: 2,
    strokeColor: 0xe6edf3,
    strokeAlpha: 0.5,
    fillAlpha: 0.8,
    defaultColor: 0x1f6feb,
  },

  // Outcome node specific
  outcome: {
    fillColor: 0x161b22,
    strokeColor: 0x8df4a3,
    strokeAlpha: 0.8,
  },

  // Edge rendering
  edge: {
    width: 2,
    color: 0x30363d,
    dominatedAlpha: 0.3,
    labelOffset: 20,
  },

  // Layout parameters
  layout: {
    nodeRadius: 24,        // Used for layout calculations
    levelHeight: 100,
    minNodeSpacing: 80,
    padding: 60,
    infoSetPadding: 8,
    infoSetSpacing: 60,    // Vertical offset between info set sublayers
  },

  // Background
  background: 0x0d1117,

  // Player colors (cycled for games with many players)
  playerColors: [0x1f6feb, 0x8b5cf6, 0x10b981, 0xf59e0b],

  // Information set colors
  infoSetColors: [0xff6b6b, 0x4ecdc4, 0xffe66d, 0xa29bfe, 0xfd79a8, 0x74b9ff],

  // Information set enclosure styling
  infoSet: {
    cornerRadius: 12,
    dashLength: 6,
    gapLength: 4,
    strokeWidth: 2,
    strokeAlpha: 0.6,
    fillAlpha: 0.08,
    labelAlpha: 0.7,
  },

  // Equilibrium markers
  equilibrium: {
    starColor: 0xffd700,  // Gold
    starSize: 16,
    borderColor: 0xffd700, // Gold border for matrix cells
    borderWidth: 3,
  },

  // Matrix (normal form) rendering
  matrix: {
    cellWidth: 80,
    cellHeight: 50,
    headerWidth: 80,
    headerHeight: 30,
    cellBackground: 0x161b22,
    headerBackground: 0x21262d,
    borderColor: 0x30363d,
    dominatedAlpha: 0.4,
  },

  // Warning/validation markers
  warning: {
    color: 0xf0a93b,
    iconSize: 10,
    iconAlpha: 0.7,
  },

  // Typography
  text: {
    fontFamily: 'Inter, system-ui, sans-serif',

    // Player labels (inside decision nodes)
    playerLabel: {
      size: 11,
      color: 0xe6edf3,
      weight: 'bold' as const,
    },

    // Action labels (on edges)
    actionLabel: {
      size: 12,
      color: 0x7ee0ff,
      dominatedColor: 0x8b949e,
    },

    // Outcome labels (below outcome nodes)
    outcomeLabel: {
      size: 10,
      color: 0x8df4a3,
    },

    // Information set labels
    infoSetLabel: {
      size: 9,
    },
  },

  // Viewport interaction settings
  viewport: {
    pinchPercent: 3,
    wheelPercent: 0.15,
    wheelSmooth: 5,
    decelerateFriction: 0.92,
  },
} as const;

// Type for the config (useful for type checking)
export type VisualConfig = typeof visualConfig;

/**
 * Get color for a player by index.
 */
export function getPlayerColor(player: string, players: string[]): number {
  const index = players.indexOf(player);
  return visualConfig.playerColors[index % visualConfig.playerColors.length];
}

/**
 * Get color for an information set by index.
 */
export function getInfoSetColor(infoSetId: string, allInfoSets: string[]): number {
  const index = allInfoSets.indexOf(infoSetId);
  return visualConfig.infoSetColors[index % visualConfig.infoSetColors.length];
}
