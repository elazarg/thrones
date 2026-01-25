/** Nash equilibrium result from analysis. */
export interface NashEquilibrium {
  description: string;
  behavior_profile: Record<string, Record<string, number>>;
  outcomes: Record<string, number>;
  strategies: Record<string, Record<string, number>>;
  payoffs: Record<string, number>;
}

/** Eliminated strategy from IESDS. */
export interface EliminatedStrategy {
  player: string;
  strategy: string;
  round: number;
}

/** IESDS result from analysis. */
export interface IESDSResult {
  eliminated: EliminatedStrategy[];
  surviving: Record<string, string[]>;
  rounds: number;
}

/** Analysis result from a plugin. */
export interface AnalysisResult {
  summary: string;
  details: {
    equilibria?: NashEquilibrium[];
    eliminated?: EliminatedStrategy[];
    surviving?: Record<string, string[]>;
    rounds?: number;
    solver?: string;
    computation_time_ms?: number;
    errors?: string[];
    warnings?: string[];
    exhaustive?: boolean;
    cancelled?: boolean;
    [key: string]: unknown;
  };
}

/** Task status from background task API. */
export type TaskStatus = 'pending' | 'running' | 'completed' | 'cancelled' | 'failed';

/** Background task from the task API. */
export interface Task {
  id: string;
  owner: string;
  status: TaskStatus;
  plugin_name: string;
  game_id: string;
  config: Record<string, unknown>;
  result: AnalysisResult | null;
  error: string | null;
  created_at: number;
  started_at: number | null;
  completed_at: number | null;
}
