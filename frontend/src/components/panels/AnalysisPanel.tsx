import { useState } from 'react';
import { useAnalysisStore, useGameStore } from '../../stores';
import type { NashEquilibrium } from '../../types';
import './AnalysisPanel.css';

/**
 * Convert a decimal probability to a simple fraction string.
 */
function toFraction(decimal: number): string {
  if (decimal === 0) return '0';
  if (decimal === 1) return '1';

  const denominators = [2, 3, 4, 5, 6, 8, 10, 12];
  for (const d of denominators) {
    const n = Math.round(decimal * d);
    if (Math.abs(n / d - decimal) < 0.0001) {
      const gcd = (a: number, b: number): number => (b === 0 ? a : gcd(b, a % b));
      const g = gcd(n, d);
      const num = n / g;
      const den = d / g;
      if (den === 1) return `${num}`;
      return `${num}/${den}`;
    }
  }
  return decimal.toFixed(2);
}

export function AnalysisPanel() {
  const resultsByType = useAnalysisStore((state) => state.resultsByType);
  const loadingAnalysis = useAnalysisStore((state) => state.loadingAnalysis);
  const selectedIndex = useAnalysisStore((state) => state.selectedEquilibriumIndex);
  const selectedAnalysisId = useAnalysisStore((state) => state.selectedAnalysisId);
  const selectEquilibrium = useAnalysisStore((state) => state.selectEquilibrium);
  const runAnalysis = useAnalysisStore((state) => state.runAnalysis);
  const cancelAnalysis = useAnalysisStore((state) => state.cancelAnalysis);

  const currentGameId = useGameStore((state) => state.currentGameId);

  // Track which sections are expanded
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  // Track current max_equilibria for the NE backoff (1 → 2 → 4 → 8 → ...)
  const [neMaxEquilibria, setNeMaxEquilibria] = useState(1);

  const toggleSection = (id: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // --- Pure NE ---
  const handleRunPure = () => {
    if (!currentGameId) return;
    runAnalysis(currentGameId, 'pure-ne', { solver: 'pure' });
    setExpandedSections(prev => new Set(prev).add('pure-ne'));
  };

  // --- Nash Equilibrium with backoff ---
  const handleRunNE = (maxEq: number) => {
    if (!currentGameId) return;
    setNeMaxEquilibria(maxEq);
    runAnalysis(currentGameId, 'nash', { solver: 'quick', maxEquilibria: maxEq });
    setExpandedSections(prev => new Set(prev).add('nash'));
  };

  const handleFindMoreNE = () => {
    const nextMax = neMaxEquilibria * 2;
    handleRunNE(nextMax);
  };

  // --- Approximate NE ---
  const handleRunApprox = () => {
    if (!currentGameId) return;
    runAnalysis(currentGameId, 'approx-ne', { solver: 'approximate' });
    setExpandedSections(prev => new Set(prev).add('approx-ne'));
  };

  if (!currentGameId) {
    return (
      <div className="analysis-panel">
        <h3>Analysis</h3>
        <p className="empty">Select a game to analyze</p>
      </div>
    );
  }

  // Results for each analysis type
  const pureResult = resultsByType['pure-ne'];
  const nashResult = resultsByType['nash'];
  const approxResult = resultsByType['approx-ne'];

  return (
    <div className="analysis-panel">
      <h3>Analysis</h3>

      <div className="analysis-sections">
        {/* Pure NE */}
        <AnalysisSection
          name="Pure NE"
          description="Find all pure-strategy Nash equilibria"
          result={pureResult}
          isLoading={loadingAnalysis === 'pure-ne'}
          isExpanded={expandedSections.has('pure-ne')}
          selectedIndex={selectedAnalysisId === 'pure-ne' ? selectedIndex : null}
          onToggle={() => toggleSection('pure-ne')}
          onRun={handleRunPure}
          onCancel={cancelAnalysis}
          onSelectEquilibrium={(index) => selectEquilibrium('pure-ne', index)}
        />

        {/* Nash Equilibrium (with backoff) */}
        <AnalysisSection
          name="Nash Equilibrium"
          description="Find Nash equilibria (click 'Find more' to search deeper)"
          result={nashResult}
          isLoading={loadingAnalysis === 'nash'}
          isExpanded={expandedSections.has('nash')}
          selectedIndex={selectedAnalysisId === 'nash' ? selectedIndex : null}
          onToggle={() => toggleSection('nash')}
          onRun={() => handleRunNE(1)}
          onCancel={cancelAnalysis}
          onSelectEquilibrium={(index) => selectEquilibrium('nash', index)}
          extraFooter={
            nashResult && !nashResult.details.exhaustive ? (
              <span className="rerun-link" onClick={(e) => { e.stopPropagation(); handleFindMoreNE(); }}>
                Find more (up to {neMaxEquilibria * 2})
              </span>
            ) : null
          }
        />

        {/* Approximate NE */}
        <AnalysisSection
          name="Approximate NE"
          description="Fast approximate equilibrium via simplicial subdivision"
          result={approxResult}
          isLoading={loadingAnalysis === 'approx-ne'}
          isExpanded={expandedSections.has('approx-ne')}
          selectedIndex={selectedAnalysisId === 'approx-ne' ? selectedIndex : null}
          onToggle={() => toggleSection('approx-ne')}
          onRun={handleRunApprox}
          onCancel={cancelAnalysis}
          onSelectEquilibrium={(index) => selectEquilibrium('approx-ne', index)}
        />

        {/* Future analyses */}
        <div className="analysis-section">
          <div className="analysis-trigger disabled" title="Iteratively eliminate dominated strategies">
            <span className="trigger-icon">▶</span>
            <span className="trigger-text">IESDS</span>
            <div className="trigger-badges">
              <span className="coming-soon-badge">Soon</span>
            </div>
          </div>
        </div>

        <div className="analysis-section">
          <div className="analysis-trigger disabled" title="Check if a strategy profile is an equilibrium">
            <span className="trigger-icon">▶</span>
            <span className="trigger-text">Verify Profile</span>
            <div className="trigger-badges">
              <span className="coming-soon-badge">Soon</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface AnalysisSectionProps {
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

function AnalysisSection({
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
          {Object.entries(equilibrium.behavior_profile).map(([player, strategies]) => {
            // Filter to only show strategies with non-zero probability
            const activeStrategies = Object.entries(strategies).filter(([, prob]) => prob > 0);
            return (
              <div key={player} className="player-strategy">
                <span className="player-name">{player}:</span>
                {activeStrategies.map(([strategy, prob]) => (
                  <span key={strategy} className="strategy">
                    {strategy}{prob < 1 ? ` (${toFraction(prob)})` : ''}
                  </span>
                ))}
              </div>
            );
          })}
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
