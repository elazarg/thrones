import type { AnalysisSectionResult } from '../../../types';
import { isEvolutionaryStabilityResult } from '../../../types';

export interface EvolutionaryStabilityRendererProps {
  result: AnalysisSectionResult;
}

export function EvolutionaryStabilityRenderer({ result }: EvolutionaryStabilityRendererProps) {
  const details = isEvolutionaryStabilityResult(result?.details) ? result.details : null;

  if (!details) {
    return (
      <div className="analysis-result-text">
        {result?.summary}
      </div>
    );
  }

  return (
    <div className="evolutionary-result">
      <p className="result-summary">{result?.summary}</p>

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
    </div>
  );
}
