/** Nash equilibrium result from analysis. */
export interface NashEquilibrium {
  description: string;
  behavior_profile: Record<string, Record<string, number>>;
  outcomes?: Record<string, number>;
  strategies: Record<string, Record<string, number>>;
  payoffs?: Record<string, number>;
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

// Type guards for runtime validation

/** Check if value is a NashEquilibrium array. */
export function isNashEquilibriumArray(value: unknown): value is NashEquilibrium[] {
  if (!Array.isArray(value)) return false;
  return value.every(
    (item) =>
      typeof item === 'object' &&
      item !== null &&
      'description' in item &&
      'behavior_profile' in item &&
      'strategies' in item
  );
}

/** Check if value is an EliminatedStrategy array. */
export function isEliminatedStrategyArray(value: unknown): value is EliminatedStrategy[] {
  if (!Array.isArray(value)) return false;
  return value.every(
    (item) =>
      typeof item === 'object' &&
      item !== null &&
      'player' in item &&
      'strategy' in item &&
      'round' in item
  );
}

/** Check if value is a surviving strategies record. */
export function isSurvivingStrategies(value: unknown): value is Record<string, string[]> {
  if (typeof value !== 'object' || value === null) return false;
  return Object.values(value).every(
    (v) => Array.isArray(v) && v.every((s) => typeof s === 'string')
  );
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
