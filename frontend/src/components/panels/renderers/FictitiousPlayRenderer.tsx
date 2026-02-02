import type { AnalysisSectionResult } from '../../../types';

export interface FictitiousPlayRendererProps {
  result: AnalysisSectionResult;
}

interface FictitiousPlayData {
  strategy: Record<string, Record<string, number>>;
  algorithm: string;
  iterations: number;
  players?: string[];
}

function isFictitiousPlayData(details: unknown): details is FictitiousPlayData {
  return (
    typeof details === 'object' &&
    details !== null &&
    'strategy' in details &&
    'iterations' in details
  );
}

// Format probability as fraction or decimal
function formatProb(p: number): string {
  if (p === 0) return '0';
  if (p === 1) return '1';
  if (Math.abs(p - 0.5) < 0.001) return '1/2';
  if (Math.abs(p - 1/3) < 0.001) return '1/3';
  if (Math.abs(p - 2/3) < 0.001) return '2/3';
  if (Math.abs(p - 0.25) < 0.001) return '1/4';
  if (Math.abs(p - 0.75) < 0.001) return '3/4';
  return p.toFixed(3);
}

export function FictitiousPlayRenderer({ result }: FictitiousPlayRendererProps) {
  const details = isFictitiousPlayData(result?.details) ? result.details : null;

  if (!details) {
    return (
      <div className="analysis-result-text">
        {result?.summary}
      </div>
    );
  }

  const { strategy, iterations } = details;
  const infoStates = Object.keys(strategy);

  return (
    <div className="fictitious-play-result">
      <p className="result-summary">{result?.summary}</p>

      <div className="fp-stats">
        <div className="stat">
          <span className="stat-label">Iterations:</span>
          <span className="stat-value">{iterations}</span>
        </div>
      </div>

      {infoStates.length > 0 && (
        <div className="strategy-profile">
          <h4 className="strategy-header">Strategy Profile</h4>
          <div className="info-states">
            {infoStates.slice(0, 10).map(infoState => {
              const actions = strategy[infoState];
              const actionEntries = Object.entries(actions).filter(([, p]) => p > 0.001);

              return (
                <div key={infoState} className="info-state-row">
                  <span className="info-state-name" title={infoState}>
                    {infoState.length > 30 ? infoState.slice(0, 30) + '...' : infoState}
                  </span>
                  <span className="info-state-actions">
                    {actionEntries.map(([action, prob], i) => (
                      <span key={action} className="action-prob">
                        {i > 0 && ', '}
                        {action}: {formatProb(prob)}
                      </span>
                    ))}
                  </span>
                </div>
              );
            })}
            {infoStates.length > 10 && (
              <p className="more-states">...and {infoStates.length - 10} more information states</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
