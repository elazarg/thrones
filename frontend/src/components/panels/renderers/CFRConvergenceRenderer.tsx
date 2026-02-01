import { useMemo } from 'react';
import type { AnalysisSectionResult } from '../../../types';
import { isCFRConvergenceResult } from '../../../types';
import { LineChart } from '../../charts/LineChart';

export interface CFRConvergenceRendererProps {
  result: AnalysisSectionResult;
}

export function CFRConvergenceRenderer({ result }: CFRConvergenceRendererProps) {
  const details = isCFRConvergenceResult(result?.details) ? result.details : null;

  // Transform convergence history for Recharts
  const chartData = useMemo(() => {
    if (!details?.convergence_history) return [];
    return details.convergence_history.map((point) => ({
      iteration: point.iteration,
      exploitability: point.exploitability,
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
    <div className="cfr-convergence-result">
      <p className="result-summary">{result?.summary}</p>

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
    </div>
  );
}
