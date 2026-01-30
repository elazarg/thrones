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

// Type guards and helpers for runtime validation

/** Generic analysis result shape used by section components. */
export type AnalysisSectionResult = { summary: string; details: Record<string, unknown> } | null;

/** Check if an analysis result represents an error. */
export function isAnalysisError(result: AnalysisSectionResult): boolean {
  if (!result) return false;
  return result.summary?.startsWith('Error:') || !!result.details?.error;
}

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

// --- EGTTools result types ---

/** Replicator dynamics result. */
export interface ReplicatorDynamicsResult {
  trajectory: number[][];
  times: number[];
  strategy_labels: string[];
  initial_state: number[];
  final_state: number[];
  time_steps: number;
  dt: number;
}

/** Evolutionary stability result. */
export interface EvolutionaryStabilityResult {
  stationary_distribution: Record<string, number>;
  fixation_probabilities: Record<string, number>;
  population_size: number;
  mutation_rate: number;
  intensity_of_selection: number;
  strategy_labels: string[];
}

/** Check if details contains replicator dynamics result. */
export function isReplicatorDynamicsResult(details: unknown): details is ReplicatorDynamicsResult {
  return (
    typeof details === 'object' &&
    details !== null &&
    'trajectory' in details &&
    'times' in details &&
    'strategy_labels' in details
  );
}

/** Check if details contains evolutionary stability result. */
export function isEvolutionaryStabilityResult(details: unknown): details is EvolutionaryStabilityResult {
  return (
    typeof details === 'object' &&
    details !== null &&
    'stationary_distribution' in details &&
    'fixation_probabilities' in details
  );
}

// --- OpenSpiel result types ---

/** CFR convergence history point. */
export interface ConvergencePoint {
  iteration: number;
  exploitability: number;
}

/** CFR convergence result. */
export interface CFRConvergenceResult {
  final_exploitability: number;
  iterations: number;
  algorithm: string;
  convergence_history: ConvergencePoint[];
}

/** Exploitability result. */
export interface ExploitabilityResult {
  nash_conv: number;
  quality: string;
  policy_type: string;
}

/** Check if details contains CFR convergence result. */
export function isCFRConvergenceResult(details: unknown): details is CFRConvergenceResult {
  return (
    typeof details === 'object' &&
    details !== null &&
    'convergence_history' in details &&
    'final_exploitability' in details
  );
}

/** Check if details contains exploitability result. */
export function isExploitabilityResult(details: unknown): details is ExploitabilityResult {
  return (
    typeof details === 'object' &&
    details !== null &&
    'nash_conv' in details &&
    'quality' in details
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
