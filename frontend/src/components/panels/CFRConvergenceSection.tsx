import { useMemo } from 'react';
import { isCFRConvergenceResult, isAnalysisError } from '../../types';
import { LineChart } from '../charts/LineChart';

export interface CFRConvergenceSectionProps {
  result: { summary: string; details: Record<string, unknown> } | null;
  isLoading: boolean;
  isExpanded: boolean;
  disabled?: boolean;
  disabledReason?: string;
  onToggle: () => void;
  onRun: () => void;
  onCancel: () => void;
}

export function CFRConvergenceSection({
  result,
  isLoading,
  isExpanded,
  disabled,
  disabledReason,
  onToggle,
  onRun,
  onCancel,
}: CFRConvergenceSectionProps) {
  const hasResult = !!result;
  const canExpand = (hasResult || isLoading) && !disabled;
  const details = isCFRConvergenceResult(result?.details) ? result.details : null;
  const isError = isAnalysisError(result);

  // Transform convergence history for Recharts
  const chartData = useMemo(() => {
    if (!details?.convergence_history) return [];
    return details.convergence_history.map((point) => ({
      iteration: point.iteration,
      exploitability: point.exploitability,
    }));
  }, [details]);

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
        title={disabled ? disabledReason : "Run CFR and track exploitability convergence"}
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
        <span className="trigger-text">CFR Convergence</span>

        <div className="trigger-badges">
          {disabled && (
            <span className="platform-badge">Unavailable</span>
          )}
          {result?.details.computation_time_ms !== undefined && (
            <span className="timing-badge">{result.details.computation_time_ms as number}ms</span>
          )}
          {details && (
            <span className="count-badge">{details.iterations} iter</span>
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
              <span>Running CFR...</span>
            </div>
          )}

          {hasResult && details && (
            <div className="cfr-convergence-result">
              <p className="result-summary">{result.summary}</p>

              {chartData.length > 0 && (
                <div className="analysis-chart">
                  <LineChart
                    data={chartData}
                    xKey="iteration"
                    lines={[
                      { key: 'exploitability', name: 'Exploitability', color: '#58a6ff' },
                    ]}
                    xLabel="Iterations"
                    yLabel="Exploitability"
                    height={160}
                  />
                </div>
              )}

              <div className="convergence-stats">
                <div className="stat">
                  <span className="stat-label">Final exploitability:</span>
                  <span className="stat-value">{details.final_exploitability.toFixed(6)}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Algorithm:</span>
                  <span className="stat-value">{details.algorithm}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Iterations:</span>
                  <span className="stat-value">{details.iterations}</span>
                </div>
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
