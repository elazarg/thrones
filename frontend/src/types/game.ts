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
