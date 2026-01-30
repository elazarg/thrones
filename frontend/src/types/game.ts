/**
 * Game format - the underlying data model.
 * Determines what data is available and what conversions are possible.
 */
export enum GameFormat {
  Vegas = 'vegas',       // Vegas DSL source code
  MAID = 'maid',         // Multi-Agent Influence Diagram
  Extensive = 'extensive', // Extensive Form Game (tree structure)
  Normal = 'normal',     // Normal Form Game (matrix)
}

/**
 * View format - how a game is visually presented.
 * Independent of game format; some views require conversion.
 */
export enum ViewFormat {
  Code = 'code',         // Source code editor (native for Vegas)
  MAIDDiagram = 'maid',  // MAID influence diagram
  Tree = 'tree',         // Extensive form tree
  Matrix = 'matrix',     // Normal form payoff matrix
  // Future: Table = 'table', // Tabular view (could work for Vegas)
}

/**
 * Get the native view format for a game format.
 * This is the view that can display the game without conversion.
 */
export function getNativeViewFormat(gameFormat: GameFormat): ViewFormat {
  switch (gameFormat) {
    case GameFormat.Vegas:
      return ViewFormat.Code;
    case GameFormat.MAID:
      return ViewFormat.MAIDDiagram;
    case GameFormat.Extensive:
      return ViewFormat.Tree;
    case GameFormat.Normal:
      return ViewFormat.Matrix;
  }
}

/**
 * Get all view formats that could potentially display a game format.
 * Some may require conversion (checked via backend).
 */
export function getPossibleViewFormats(gameFormat: GameFormat): ViewFormat[] {
  switch (gameFormat) {
    case GameFormat.Vegas:
      // Vegas can show as code (native), or convert to MAID/Tree/Matrix
      return [ViewFormat.Code, ViewFormat.MAIDDiagram, ViewFormat.Tree, ViewFormat.Matrix];
    case GameFormat.MAID:
      // MAID can show as diagram (native), or convert to Tree/Matrix
      return [ViewFormat.MAIDDiagram, ViewFormat.Tree, ViewFormat.Matrix];
    case GameFormat.Extensive:
      // EFG can show as tree (native), or convert to Matrix
      return [ViewFormat.Tree, ViewFormat.Matrix];
    case GameFormat.Normal:
      // NFG can show as matrix (native), or convert to Tree
      return [ViewFormat.Matrix, ViewFormat.Tree];
  }
}

/**
 * Get the game format required to render a view format.
 * Returns null if the view is native (no conversion needed).
 */
export function getRequiredGameFormat(viewFormat: ViewFormat): GameFormat | null {
  switch (viewFormat) {
    case ViewFormat.Code:
      return null; // Only Vegas has code, and it's native
    case ViewFormat.MAIDDiagram:
      return GameFormat.MAID;
    case ViewFormat.Tree:
      return GameFormat.Extensive;
    case ViewFormat.Matrix:
      return GameFormat.Normal;
  }
}

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
export interface ExtensiveFormGame {
  id: string;
  title: string;
  description?: string;
  players: string[];
  root: string;
  nodes: Record<string, DecisionNode>;
  outcomes: Record<string, Outcome>;
  tags: string[];
  format_name?: 'extensive';
  /** Mapping from MAID decision node IDs to EFG node IDs (only present when converted from MAID) */
  maid_to_efg_nodes?: Record<string, string[]>;
}

/**
 * Normal form (strategic form) game represented as a payoff matrix.
 * Used for 2-player simultaneous games.
 */
export interface NormalFormGame {
  id: string;
  title: string;
  description?: string;
  players: [string, string]; // Exactly 2 players
  strategies: [string[], string[]]; // Strategies per player
  payoffs: [number, number][][]; // [row][col] -> [P1 payoff, P2 payoff]
  tags: string[];
  format_name?: 'normal';
  /** Mapping from MAID decision node ID to player name (only present when converted from MAID) */
  maid_decision_to_player?: Record<string, string>;
}

/** Node in a MAID (Multi-Agent Influence Diagram) */
export interface MAIDNode {
  id: string;
  type: 'decision' | 'utility' | 'chance';
  agent?: string;
  domain?: (string | number)[];
}

/** Edge in a MAID */
export interface MAIDEdge {
  source: string;
  target: string;
}

/** Conditional probability distribution for a node */
export interface TabularCPD {
  node: string;
  parents: string[];
  values: number[][];
}

/** Multi-Agent Influence Diagram game */
export interface MAIDGame {
  id: string;
  title: string;
  description?: string;
  agents: string[];
  nodes: MAIDNode[];
  edges: MAIDEdge[];
  cpds: TabularCPD[];
  tags: string[];
  format_name: 'maid';
}

/** Vegas DSL game - stored as source code */
export interface VegasGame {
  id: string;
  title: string;
  description?: string;
  source_code: string;
  players: string[];
  tags: string[];
  format_name: 'vegas';
}

/** Union type for any game representation */
export type AnyGame = ExtensiveFormGame | NormalFormGame | MAIDGame | VegasGame;

/** Type guard to check if a game is normal form */
export function isNormalFormGame(game: AnyGame): game is NormalFormGame {
  return 'strategies' in game && 'payoffs' in game && !('nodes' in game);
}

/** Type guard to check if a game is extensive form */
export function isExtensiveFormGame(game: AnyGame): game is ExtensiveFormGame {
  return 'nodes' in game && 'root' in game;
}

/** Type guard to check if a game is a MAID */
export function isMAIDGame(game: AnyGame): game is MAIDGame {
  return 'format_name' in game && (game as MAIDGame).format_name === 'maid';
}

/** Type guard to check if a game is Vegas format */
export function isVegasGame(game: AnyGame): game is VegasGame {
  return 'format_name' in game && (game as VegasGame).format_name === 'vegas';
}

/** Check if a normal-form game is symmetric (both players have same number of strategies) */
export function isSymmetricGame(game: AnyGame): boolean {
  if (!isNormalFormGame(game)) {
    return false;
  }
  const strategies = game.strategies;
  if (!strategies || strategies.length < 2) {
    return false;
  }
  return strategies[0].length === strategies[1].length;
}

/** Check if a game should be displayed as matrix (2-player strategic form) */
export function shouldShowAsMatrix(game: AnyGame): boolean {
  if (isMAIDGame(game) || isVegasGame(game)) {
    return false; // MAID and Vegas games don't show as matrix
  }
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
  description?: string;
  players: string[];
  format: 'extensive' | 'normal' | 'maid' | 'vegas';
  tags: string[];
  /** Conversion info - only populated when fetched via /api/games/{id}/summary */
  conversions?: Record<string, ConversionInfo>;
}

/** Compile target advertised by a plugin. */
export interface CompileTarget {
  id: string;
  type: 'code';
  language: string;
  label: string;
}

/** Plugin status from /api/plugins/status */
export interface PluginStatus {
  name: string;
  healthy: boolean;
  port: number | null;
  analyses: string[];
  compile_targets?: CompileTarget[];
}

/** Compiled code result stored per game. */
export interface CompiledCode {
  targetId: string;
  language: string;
  label: string;
  content: string;
}
