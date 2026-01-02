/** Nash equilibrium result from analysis. */
export interface NashEquilibrium {
  description: string;
  behavior_profile: Record<string, Record<string, number>>;
  outcomes: Record<string, number>;
  strategies: Record<string, Record<string, number>>;
  payoffs: Record<string, number>;
}

/** Analysis result from a plugin. */
export interface AnalysisResult {
  summary: string;
  details: {
    equilibria?: NashEquilibrium[];
    solver?: string;
    computation_time_ms?: number;
    errors?: string[];
    warnings?: string[];
    [key: string]: unknown;
  };
}
