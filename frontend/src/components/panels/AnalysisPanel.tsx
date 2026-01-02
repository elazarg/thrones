import { useAnalysisStore, useGameStore } from '../../stores';
import type { NashEquilibrium } from '../../types';
import './AnalysisPanel.css';

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

  // Complete state - show results
  return (
    <div className="analysis-panel">
      <h3>Analysis</h3>
      {results.map((result, resultIndex) => (
        <div key={resultIndex} className="analysis-card">
          <div className="analysis-header">
            <strong>{result.summary}</strong>
            {result.details.solver && (
              <span className="solver">{result.details.solver}</span>
            )}
          </div>
          {result.details.equilibria && (
            <div className="equilibria-list">
              {result.details.equilibria.map((eq, eqIndex) => (
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
      ))}
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
                  {strategy} ({(prob * 100).toFixed(0)}%)
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
