import type { NashEquilibrium } from '../../types';
import { EquilibriumCard } from './EquilibriumCard';

export interface AnalysisSectionProps {
  name: string;
  description: string;
  result: { summary: string; details: Record<string, unknown> } | null;
  isLoading: boolean;
  isExpanded: boolean;
  selectedIndex: number | null;
  onToggle: () => void;
  onRun: () => void;
  onCancel: () => void;
  onSelectEquilibrium: (index: number | null) => void;
  extraFooter?: React.ReactNode;
}

export function AnalysisSection({
  name,
  description,
  result,
  isLoading,
  isExpanded,
  selectedIndex,
  onToggle,
  onRun,
  onCancel,
  onSelectEquilibrium,
  extraFooter,
}: AnalysisSectionProps) {
  const hasResult = !!result;
  const canExpand = hasResult || isLoading;
  const equilibria = result?.details.equilibria as NashEquilibrium[] | undefined;

  const handleHeaderClick = () => {
    if (canExpand) {
      onToggle();
    } else {
      onRun();
    }
  };

  return (
    <div className={`analysis-section ${isExpanded && canExpand ? 'expanded' : ''}`}>
      <div
        className={`analysis-trigger ${hasResult ? 'has-result' : ''}`}
        onClick={handleHeaderClick}
        title={description}
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
        <span className="trigger-text">{name}</span>

        <div className="trigger-badges">
          {result?.details.computation_time_ms !== undefined && (
            <span className="timing-badge">{result.details.computation_time_ms as number}ms</span>
          )}
          {equilibria && (
            <span className="count-badge">
              {equilibria.length}
              {!result?.details.exhaustive && '+'}
            </span>
          )}
        </div>

        {isLoading && (
          <span className="stop-link" onClick={(e) => { e.stopPropagation(); onCancel(); }}>Stop</span>
        )}
      </div>

      {isExpanded && canExpand && (
        <div className="analysis-content">
          {isLoading && !result && (
            <div className="analysis-loading">
              <span>Computing...</span>
            </div>
          )}

          {equilibria && (
            <div className="equilibria-list">
              <p className="equilibria-hint">Click to highlight on canvas</p>
              {equilibria.map((eq, eqIndex) => (
                <EquilibriumCard
                  key={eqIndex}
                  equilibrium={eq}
                  index={eqIndex}
                  isSelected={selectedIndex === eqIndex}
                  onSelect={() => onSelectEquilibrium(selectedIndex === eqIndex ? null : eqIndex)}
                />
              ))}
              <div className="analysis-section-footer">
                {extraFooter}
                <span className="rerun-link" onClick={(e) => { e.stopPropagation(); onRun(); }}>
                  Recompute
                </span>
              </div>
            </div>
          )}

          {result && !equilibria && (
            <div className="analysis-result-text">
              {result.summary}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
