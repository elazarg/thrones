import type { AnalysisSectionResult } from '../../../types';

export interface DecisionRelevanceRendererProps {
  result: AnalysisSectionResult;
}

interface RelevanceData {
  decisions: string[];
  r_reachable: Record<string, string[]>;
  s_reachable: Record<string, string[]>;
}

function isRelevanceData(details: unknown): details is RelevanceData {
  return (
    typeof details === 'object' &&
    details !== null &&
    'decisions' in details &&
    'r_reachable' in details &&
    's_reachable' in details
  );
}

export function DecisionRelevanceRenderer({ result }: DecisionRelevanceRendererProps) {
  const details = isRelevanceData(result?.details) ? result.details : null;

  if (!details) {
    return (
      <div className="analysis-result-text">
        {result?.summary}
      </div>
    );
  }

  const { decisions, r_reachable, s_reachable } = details;
  const hasRelationships = Object.values(r_reachable).some(arr => arr.length > 0) ||
                           Object.values(s_reachable).some(arr => arr.length > 0);

  return (
    <div className="decision-relevance-result">
      <p className="result-summary">{result?.summary}</p>

      {!hasRelationships ? (
        <p className="no-relationships">No strategic dependencies between decisions</p>
      ) : (
        <div className="relevance-tables">
          {/* R-Reachability */}
          <div className="relevance-section">
            <h4 className="relevance-header">R-Reachable</h4>
            <p className="relevance-hint">D1 r-reaches D2: D1's value can affect D2's optimal action</p>
            <div className="relevance-list">
              {decisions.map(d1 => {
                const reaches = r_reachable[d1] || [];
                if (reaches.length === 0) return null;
                return (
                  <div key={d1} className="relevance-row">
                    <span className="decision-from">{d1}</span>
                    <span className="arrow">→</span>
                    <span className="decisions-to">{reaches.join(', ')}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* S-Reachability */}
          <div className="relevance-section">
            <h4 className="relevance-header">S-Reachable</h4>
            <p className="relevance-hint">D1 s-reaches D2: D1's action can strategically influence D2</p>
            <div className="relevance-list">
              {decisions.map(d1 => {
                const reaches = s_reachable[d1] || [];
                if (reaches.length === 0) return null;
                return (
                  <div key={d1} className="relevance-row">
                    <span className="decision-from">{d1}</span>
                    <span className="arrow">→</span>
                    <span className="decisions-to">{reaches.join(', ')}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
