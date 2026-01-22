/** Terminal node outcome with payoffs per player. */
export interface Outcome {
  label: string;
  payoffs: Record<string, number>;
}

/** Action available from a decision node. */
export interface Action {
  label: string;
  probability?: number;
  target?: string;
  warning?: string;
}

/** Node controlled by a single player. */
export interface DecisionNode {
  id: string;
  player: string;
  actions: Action[];
  information_set?: string;
  warning?: string;
}

/** Minimal representation of an extensive-form game. */
export interface Game {
  id: string;
  title: string;
  players: string[];
  root: string;
  nodes: Record<string, DecisionNode>;
  outcomes: Record<string, Outcome>;
  version: string;
  tags: string[];
}

/**
 * Normal form (strategic form) game represented as a payoff matrix.
 * Used for 2-player simultaneous games.
 */
export interface NormalFormGame {
  id: string;
  title: string;
  players: [string, string]; // Exactly 2 players
  strategies: [string[], string[]]; // Strategies per player
  payoffs: [number, number][][]; // [row][col] -> [P1 payoff, P2 payoff]
  version: string;
  tags: string[];
}

/** Union type for any game representation */
export type AnyGame = Game | NormalFormGame;

/** Type guard to check if a game is normal form */
export function isNormalFormGame(game: AnyGame): game is NormalFormGame {
  return 'strategies' in game && 'payoffs' in game && !('nodes' in game);
}

/** Type guard to check if a game is extensive form */
export function isExtensiveFormGame(game: AnyGame): game is Game {
  return 'nodes' in game && 'root' in game;
}

/** Check if a game should be displayed as matrix (2-player strategic form) */
export function shouldShowAsMatrix(game: AnyGame): boolean {
  if (isNormalFormGame(game)) {
    return true;
  }
  // Extensive form games with strategic-form tag and 2 players can be shown as matrix
  return game.tags.includes('strategic-form') && game.players.length === 2;
}

/** Information about a possible conversion. */
export interface ConversionInfo {
  possible: boolean;
  warnings: string[];
  blockers: string[];
}

/** Lightweight game summary for listings. */
export interface GameSummary {
  id: string;
  title: string;
  players: string[];
  version: string;
  format: 'extensive' | 'normal';
  conversions: Record<string, ConversionInfo>;
}
