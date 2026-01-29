import { useConfigStore, type SolverType } from '../../../stores';

const SOLVER_OPTIONS: { value: SolverType; label: string }[] = [
  { value: 'quick', label: 'Quick' },
  { value: 'exhaustive', label: 'Exhaustive' },
  { value: 'pure', label: 'Pure Only' },
  { value: 'approximate', label: 'Approximate' },
];

export function AnalysisSettings() {
  const defaultSolver = useConfigStore((s) => s.defaultSolver);
  const defaultMaxEquilibria = useConfigStore((s) => s.defaultMaxEquilibria);
  const setDefaultSolver = useConfigStore((s) => s.setDefaultSolver);
  const setDefaultMaxEquilibria = useConfigStore((s) => s.setDefaultMaxEquilibria);

  return (
    <>
      <div className="config-field">
        <div className="config-field-info">
          <span className="config-field-label">Default Solver</span>
          <span className="config-field-hint">Algorithm for finding equilibria</span>
        </div>
        <select
          className="config-select"
          value={defaultSolver}
          onChange={(e) => setDefaultSolver(e.target.value as SolverType)}
        >
          {SOLVER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="config-field">
        <div className="config-field-info">
          <span className="config-field-label">Max Equilibria</span>
          <span className="config-field-hint">Limit results (1-100)</span>
        </div>
        <input
          type="number"
          className="config-input"
          value={defaultMaxEquilibria}
          min={1}
          max={100}
          onChange={(e) => {
            const val = parseInt(e.target.value, 10);
            if (!isNaN(val) && val >= 1 && val <= 100) {
              setDefaultMaxEquilibria(val);
            }
          }}
        />
      </div>
    </>
  );
}
