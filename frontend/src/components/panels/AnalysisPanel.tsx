import { useState } from 'react';
import { useAnalysisStore, useGameStore } from '../../stores';
import type { AnalysisOptions } from '../../stores/analysisStore';
import type { NashEquilibrium, AnalysisResult } from '../../types';
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

/** Definition of an analysis type */
interface AnalysisType {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  options?: AnalysisOptions;
}

const ANALYSIS_TYPES: AnalysisType[] = [
  { id: 'nash', name: 'Nash Equilibrium', description: 'Find all Nash equilibria (exhaustive)', enabled: true, options: { solver: 'exhaustive' } },
  { id: 'quick-ne', name: 'Quick NE (First Only)', description: 'Find one equilibrium quickly using LCP solver', enabled: true, options: { solver: 'quick' } },
  { id: 'pure-ne', name: 'Pure Strategy NE', description: 'Find only pure-strategy equilibria', enabled: true, options: { solver: 'pure' } },
  { id: 'approx-ne', name: 'Approximate NE', description: 'Fast approximate equilibrium via simplicial subdivision', enabled: true, options: { solver: 'approximate' } },
  { id: 'iesds', name: 'IESDS', description: 'Iteratively eliminate dominated strategies', enabled: false },
  { id: 'verify-profile', name: 'Verify Profile', description: 'Check if a strategy profile is an equilibrium', enabled: false },
];

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

  const handleRunAnalysis = (analysisId: string) => {
    if (!currentGameId) return;

    const analysis = ANALYSIS_TYPES.find(a => a.id === analysisId);
    if (!analysis?.enabled) return;

    runAnalysis(currentGameId, analysisId, analysis.options);
    // Auto-expand the section when running
    setExpandedSections(prev => new Set(prev).add(analysisId));
  };

  if (!currentGameId) {
    return (
      <div className="analysis-panel">
        <h3>Analysis</h3>
        <p className="empty">Select a game to analyze</p>
      </div>
    );
  }

  return (
    <div className="analysis-panel">
      <h3>Analysis</h3>

      {/* Analysis sections */}
      <div className="analysis-sections">
        {ANALYSIS_TYPES.map((analysis) => {
          const result = resultsByType[analysis.id];
          const isLoading = loadingAnalysis === analysis.id;
          const isSelectedSection = selectedAnalysisId === analysis.id;

          return (
            <AnalysisSection
              key={analysis.id}
              analysis={analysis}
              isExpanded={expandedSections.has(analysis.id)}
              isLoading={isLoading}
              result={result || undefined}
              selectedIndex={isSelectedSection ? selectedIndex : null}
              onToggle={() => toggleSection(analysis.id)}
              onRun={() => handleRunAnalysis(analysis.id)}
              onCancel={cancelAnalysis}
              onSelectEquilibrium={(index) => selectEquilibrium(analysis.id, index)}
            />
          );
        })}
      </div>
    </div>
  );
}

interface AnalysisSectionProps {
  analysis: AnalysisType;
  isExpanded: boolean;
  isLoading: boolean;
  result?: AnalysisResult;
  selectedIndex: number | null;
  onToggle: () => void;
  onRun: () => void;
  onCancel: () => void;
  onSelectEquilibrium: (index: number | null) => void;
}

function AnalysisSection({
  analysis,
  isExpanded,
  isLoading,
  result,
  selectedIndex,
  onToggle,
  onRun,
  onCancel,
  onSelectEquilibrium,
}: AnalysisSectionProps) {
  const hasResult = !!result;
  const canExpand = analysis.enabled && (hasResult || isLoading);

  const handleHeaderClick = () => {
    if (!analysis.enabled) return;

    if (canExpand) {
      onToggle();
    } else {
      onRun();
    }
  };

  return (
    <div className={`analysis-section ${isExpanded && canExpand ? 'expanded' : ''}`}>
      {/* Section header - clickable trigger */}
      <div
        className={`analysis-trigger ${!analysis.enabled ? 'disabled' : ''} ${hasResult ? 'has-result' : ''}`}
        onClick={handleHeaderClick}
        title={analysis.description}
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
        <span className="trigger-text">{analysis.name}</span>

        {/* Badges */}
        <div className="trigger-badges">
          {!analysis.enabled && (
            <span className="coming-soon-badge">Soon</span>
          )}
          {result?.details.computation_time_ms !== undefined && (
            <span className="timing-badge">{result.details.computation_time_ms}ms</span>
          )}
          {result?.details.equilibria && (
            <span className="count-badge">{result.details.equilibria.length}</span>
          )}
        </div>

        {/* Stop button when loading */}
        {isLoading && (
          <span className="stop-link" onClick={(e) => { e.stopPropagation(); onCancel(); }}>Stop</span>
        )}
      </div>

      {/* Collapsible content */}
      {analysis.enabled && isExpanded && canExpand && (
        <div className="analysis-content">
          {isLoading && !result && (
            <div className="analysis-loading">
              <span>Computing...</span>
            </div>
          )}

          {result?.details.equilibria && (
            <div className="equilibria-list">
              <p className="equilibria-hint">Click to highlight outcome on canvas</p>
              {result.details.equilibria.map((eq, eqIndex) => (
                <EquilibriumCard
                  key={eqIndex}
                  equilibrium={eq}
                  index={eqIndex}
                  isSelected={selectedIndex === eqIndex}
                  onSelect={() => onSelectEquilibrium(selectedIndex === eqIndex ? null : eqIndex)}
                />
              ))}
              <div className="analysis-section-footer">
                <span className="rerun-link" onClick={(e) => { e.stopPropagation(); onRun(); }}>Run again</span>
              </div>
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
          {Object.entries(equilibrium.behavior_profile).map(([player, strategies]) => (
            <div key={player} className="player-strategy">
              <span className="player-name">{player}:</span>
              {Object.entries(strategies).map(([strategy, prob]) => (
                <span key={strategy} className="strategy">
                  {strategy} ({toFraction(prob)})
                </span>
              ))}
            </div>
          ))}
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
