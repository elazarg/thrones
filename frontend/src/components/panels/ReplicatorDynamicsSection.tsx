import { useMemo } from 'react';
import { isReplicatorDynamicsResult, isAnalysisError } from '../../types';
import { LineChart } from '../charts/LineChart';

// Strategy colors for chart lines
const STRATEGY_COLORS = [
  '#58a6ff', // blue
  '#8b949e', // gray
  '#a371f7', // purple
  '#7ee787', // green
  '#ffa657', // orange
  '#ff7b72', // red
  '#79c0ff', // light blue
  '#d2a8ff', // light purple
];

export interface ReplicatorDynamicsSectionProps {
  result: { summary: string; details: Record<string, unknown> } | null;
  isLoading: boolean;
  isExpanded: boolean;
  disabled?: boolean;
  disabledReason?: string;
  onToggle: () => void;
  onRun: () => void;
  onCancel: () => void;
}

export function ReplicatorDynamicsSection({
  result,
  isLoading,
  isExpanded,
  disabled,
  disabledReason,
  onToggle,
  onRun,
  onCancel,
}: ReplicatorDynamicsSectionProps) {
  const hasResult = !!result;
  const canExpand = (hasResult || isLoading) && !disabled;
  const details = isReplicatorDynamicsResult(result?.details) ? result.details : null;
  const isError = isAnalysisError(result);

  // Transform trajectory data for Recharts
  const chartData = useMemo(() => {
    if (!details) return [];
    const { trajectory, times, strategy_labels } = details;
    return times.map((t, i) => {
      const point: Record<string, number> = { time: t };
      strategy_labels.forEach((label, j) => {
        point[label] = trajectory[i][j];
      });
      return point;
    });
  }, [details]);

  // Generate line configs
  const lines = useMemo(() => {
    if (!details) return [];
    return details.strategy_labels.map((label, i) => ({
      key: label,
      name: label,
      color: STRATEGY_COLORS[i % STRATEGY_COLORS.length],
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
        title={disabled ? disabledReason : "Simulate strategy evolution using replicator dynamics"}
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
        <span className="trigger-text">Replicator Dynamics</span>

        <div className="trigger-badges">
          {disabled && disabledReason && (
            <span className="platform-badge">{disabledReason}</span>
          )}
          {result?.details.computation_time_ms !== undefined && (
            <span className="timing-badge">{result.details.computation_time_ms as number}ms</span>
          )}
          {details && (
            <span className="count-badge">{details.time_steps} steps</span>
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
              <span>Simulating...</span>
            </div>
          )}

          {hasResult && details && (
            <div className="replicator-result">
              <p className="result-summary">{result.summary}</p>

              <div className="analysis-chart">
                <LineChart
                  data={chartData}
                  xKey="time"
                  lines={lines}
                  xLabel="Time"
                  yLabel="Frequency"
                  height={160}
                />
              </div>

              <div className="state-display">
                <div className="state-row">
                  <span className="state-label">Initial:</span>
                  {details.strategy_labels.map((label, i) => (
                    <span key={label} className="state-value">
                      <span className="strategy-name">{label}</span>
                      <span className="frequency">{(details.initial_state[i] * 100).toFixed(1)}%</span>
                    </span>
                  ))}
                </div>
                <div className="state-row">
                  <span className="state-label">Final:</span>
                  {details.strategy_labels.map((label, i) => (
                    <span key={label} className="state-value">
                      <span className="strategy-name">{label}</span>
                      <span className="frequency">{(details.final_state[i] * 100).toFixed(1)}%</span>
                    </span>
                  ))}
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
