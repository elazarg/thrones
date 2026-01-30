import { isEvolutionaryStabilityResult, isAnalysisError } from '../../types';

export interface EvolutionaryStabilitySectionProps {
  result: { summary: string; details: Record<string, unknown> } | null;
  isLoading: boolean;
  isExpanded: boolean;
  disabled?: boolean;
  disabledReason?: string;
  onToggle: () => void;
  onRun: () => void;
  onCancel: () => void;
}

export function EvolutionaryStabilitySection({
  result,
  isLoading,
  isExpanded,
  disabled,
  disabledReason,
  onToggle,
  onRun,
  onCancel,
}: EvolutionaryStabilitySectionProps) {
  const hasResult = !!result;
  const canExpand = (hasResult || isLoading) && !disabled;
  const details = isEvolutionaryStabilityResult(result?.details) ? result.details : null;
  const isError = isAnalysisError(result);

  const handleHeaderClick = () => {
    if (disabled) return;
    if (canExpand) {
      onToggle();
    } else {
      onRun();
    }
  };

  return (
    <div className={`analysis-section ${isExpanded && canExpand ? 'expanded' : ''}`}>
      <div
        className={`analysis-trigger ${hasResult && !isError ? 'has-result' : ''} ${isError ? 'has-error' : ''} ${disabled ? 'disabled' : ''}`}
        onClick={handleHeaderClick}
        title={disabled ? disabledReason : "Analyze evolutionary stability via finite population dynamics"}
      >
        <span className="trigger-icon">
          {isLoading ? (
            <span className="spinner-small"></span>
          ) : canExpand ? (
            isExpanded ? '▼' : '▶'
          ) : (
            '▶'
          )}
        </span>
        <span className="trigger-text">Evolutionary Stability</span>

        <div className="trigger-badges">
          {disabled && disabledReason && (
            <span className="platform-badge">{disabledReason}</span>
          )}
          {result?.details.computation_time_ms !== undefined && (
            <span className="timing-badge">{result.details.computation_time_ms as number}ms</span>
          )}
          {details && (
            <span className="count-badge">N={details.population_size}</span>
          )}
        </div>

        {isLoading && (
          <button type="button" className="stop-link" onClick={(e) => { e.stopPropagation(); onCancel(); }}>Stop</button>
        )}
      </div>

      {isExpanded && canExpand && (
        <div className="analysis-content">
          {isLoading && !result && (
            <div className="analysis-loading">
              <span>Computing...</span>
            </div>
          )}

          {hasResult && details && (
            <div className="evolutionary-result">
              <p className="result-summary">{result.summary}</p>

              <div className="distribution-section">
                <p className="section-header">Stationary Distribution</p>
                <div className="distribution-bars">
                  {Object.entries(details.stationary_distribution).map(([strategy, freq]) => (
                    <div key={strategy} className="distribution-bar">
                      <span className="bar-label">{strategy}</span>
                      <div className="bar-track">
                        <div
                          className="bar-fill"
                          style={{ width: `${freq * 100}%` }}
                        />
                      </div>
                      <span className="bar-value">{(freq * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="fixation-section">
                <p className="section-header">Fixation Probabilities</p>
                <div className="fixation-table">
                  {Object.entries(details.fixation_probabilities).map(([key, prob]) => {
                    // Parse key like "Cooperate_invades_Defect"
                    const match = key.match(/(.+)_invades_(.+)/);
                    if (!match) return null;
                    const [, invader, resident] = match;
                    const neutral = 1 / details.population_size;
                    const ratio = prob / neutral;
                    return (
                      <div key={key} className="fixation-row">
                        <span className="fixation-desc">
                          <span className="strategy-name">{invader}</span>
                          <span className="fixation-arrow">→</span>
                          <span className="strategy-name">{resident}</span>
                        </span>
                        <span className={`fixation-value ${ratio > 1 ? 'favored' : ratio < 1 ? 'disfavored' : ''}`}>
                          {prob.toFixed(4)}
                          {ratio !== 1 && (
                            <span className="fixation-ratio">({ratio.toFixed(2)}×)</span>
                          )}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="params-display">
                <span>β={details.intensity_of_selection}</span>
                <span>μ={details.mutation_rate}</span>
              </div>

              <div className="analysis-section-footer">
                <button type="button" className="rerun-link" onClick={(e) => { e.stopPropagation(); onRun(); }}>
                  Recompute
                </button>
              </div>
            </div>
          )}

          {hasResult && !details && (
            <div className="analysis-result-text analysis-error">
              {result.summary}
              {isError && (
                <button type="button" className="rerun-link" onClick={(e) => { e.stopPropagation(); onRun(); }}>
                  Retry
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
