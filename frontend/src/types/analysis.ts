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
    [key: string]: unknown;
  };
}
