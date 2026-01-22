import { useAnalysisStore, useGameStore } from '../../stores';
import type { NashEquilibrium } from '../../types';
import './AnalysisPanel.css';

/**
 * Convert a decimal probability to a simple fraction string.
 */
function toFraction(decimal: number): string {
  if (decimal === 0) return '0';
  if (decimal === 1) return '1';

  const denominators = [2, 3, 4, 5, 6, 8, 10, 12];
  for (const d of denominators) {
    const n = Math.round(decimal * d);
    if (Math.abs(n / d - decimal) < 0.0001) {
      const gcd = (a: number, b: number): number => (b === 0 ? a : gcd(b, a % b));
      const g = gcd(n, d);
      const num = n / g;
      const den = d / g;
      if (den === 1) return `${num}`;
      return `${num}/${den}`;
    }
  }
  return decimal.toFixed(2);
}

export function AnalysisPanel() {
  const results = useAnalysisStore((state) => state.results);
  const loading = useAnalysisStore((state) => state.loading);
  const selectedIndex = useAnalysisStore((state) => state.selectedEquilibriumIndex);
  const selectEquilibrium = useAnalysisStore((state) => state.selectEquilibrium);
  const runAnalysis = useAnalysisStore((state) => state.runAnalysis);
  const cancelAnalysis = useAnalysisStore((state) => state.cancelAnalysis);

  const currentGameId = useGameStore((state) => state.currentGameId);

  const handleRunAnalysis = () => {
    if (currentGameId) {
      runAnalysis(currentGameId);
    }
  };

  // Idle state - show clickable trigger
  if (!loading && results.length === 0) {
    return (
      <div className="analysis-panel">
        <h3>Analysis</h3>
        {currentGameId ? (
          <div className="analysis-trigger" onClick={handleRunAnalysis}>
            <span className="trigger-icon">▶</span>
            <span className="trigger-text">Find Nash Equilibrium</span>
          </div>
        ) : (
          <p className="empty">Select a game to analyze</p>
        )}
      </div>
    );
  }

  // Running state - show spinner with stop option
  if (loading) {
    return (
      <div className="analysis-panel">
        <h3>Analysis</h3>
        <div className="analysis-running">
          <div className="running-status">
            <span className="spinner"></span>
            <span>Finding Nash Equilibrium...</span>
          </div>
          <span className="stop-link" onClick={cancelAnalysis}>Stop</span>
        </div>
      </div>
    );
  }

  // Separate validation results from equilibrium results
  const validationResult = results.find(r => r.summary.startsWith('Valid') || r.summary.startsWith('Invalid'));
  const equilibriumResult = results.find(r => r.details.equilibria);

  return (
    <div className="analysis-panel">
      <h3>Analysis</h3>

      {/* Status bar for validation */}
      {validationResult && (
        <div className={`validation-status ${validationResult.summary.startsWith('Valid') ? 'valid' : 'invalid'}`}>
          <span className="status-icon">{validationResult.summary.startsWith('Valid') ? '✓' : '✗'}</span>
          <span className="status-text">{validationResult.summary}</span>
        </div>
      )}

      {/* Equilibrium results */}
      {equilibriumResult && (
        <div className="analysis-card">
          <div className="analysis-header">
            <strong>{equilibriumResult.summary}</strong>
            <div className="analysis-badges">
              {equilibriumResult.details.solver && (
                <span className="solver">{equilibriumResult.details.solver}</span>
              )}
              {equilibriumResult.details.computation_time_ms !== undefined && (
                <span className="timing">{equilibriumResult.details.computation_time_ms}ms</span>
              )}
            </div>
          </div>
          {equilibriumResult.details.equilibria && (
            <div className="equilibria-list">
              <p className="equilibria-hint">Click to highlight outcome on canvas</p>
              {equilibriumResult.details.equilibria.map((eq, eqIndex) => (
                <EquilibriumCard
                  key={eqIndex}
                  equilibrium={eq}
                  index={eqIndex}
                  isSelected={selectedIndex === eqIndex}
                  onSelect={() => selectEquilibrium(selectedIndex === eqIndex ? null : eqIndex)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      <div className="analysis-footer">
        <span className="rerun-link" onClick={handleRunAnalysis}>Run again</span>
      </div>
    </div>
  );
}

interface EquilibriumCardProps {
  equilibrium: NashEquilibrium;
  index: number;
  isSelected: boolean;
  onSelect: () => void;
}

function EquilibriumCard({ equilibrium, index, isSelected, onSelect }: EquilibriumCardProps) {
  return (
    <button
      className={`equilibrium-card ${isSelected ? 'selected' : ''}`}
      onClick={onSelect}
    >
      <div className="eq-header">
        <span className="eq-index">#{index + 1}</span>
        <span className="eq-description">{equilibrium.description}</span>
      </div>
      <div className="eq-details">
        <div className="eq-strategies">
          <span className="label">Strategies:</span>
          {Object.entries(equilibrium.behavior_profile).map(([player, strategies]) => (
            <div key={player} className="player-strategy">
              <span className="player-name">{player}:</span>
              {Object.entries(strategies).map(([strategy, prob]) => (
                <span key={strategy} className="strategy">
                  {strategy} ({toFraction(prob)})
                </span>
              ))}
            </div>
          ))}
        </div>
        <div className="eq-payoffs">
          <span className="label">Payoffs:</span>
          {Object.entries(equilibrium.outcomes).map(([player, payoff]) => (
            <span key={player} className="payoff">
              {player}: {payoff}
            </span>
          ))}
        </div>
      </div>
    </button>
  );
}
