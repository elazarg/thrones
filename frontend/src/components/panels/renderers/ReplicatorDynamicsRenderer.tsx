import { useMemo } from 'react';
import type { AnalysisSectionResult } from '../../../types';
import { isReplicatorDynamicsResult } from '../../../types';
import { LineChart } from '../../charts/LineChart';

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

export interface ReplicatorDynamicsRendererProps {
  result: AnalysisSectionResult;
}

export function ReplicatorDynamicsRenderer({ result }: ReplicatorDynamicsRendererProps) {
  const details = isReplicatorDynamicsResult(result?.details) ? result.details : null;

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

  if (!details) {
    return (
      <div className="analysis-result-text">
        {result?.summary}
      </div>
    );
  }

  return (
    <div className="replicator-result">
      <p className="result-summary">{result?.summary}</p>

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
    </div>
  );
}
