import { useState } from 'react';
import { useAnalysisStore, useGameStore, useUIStore } from '../../stores';
import type { NashEquilibrium } from '../../types';
import { toFraction } from '../../utils/mathUtils';
import './AnalysisPanel.css';

export function AnalysisPanel() {
  const resultsByType = useAnalysisStore((state) => state.resultsByType);
  const loadingAnalysis = useAnalysisStore((state) => state.loadingAnalysis);
  const selectedIndex = useAnalysisStore((state) => state.selectedEquilibriumIndex);
  const selectedAnalysisId = useAnalysisStore((state) => state.selectedAnalysisId);
  const selectEquilibrium = useAnalysisStore((state) => state.selectEquilibrium);
  const runAnalysis = useAnalysisStore((state) => state.runAnalysis);
  const cancelAnalysis = useAnalysisStore((state) => state.cancelAnalysis);
  const isIESDSSelected = useAnalysisStore((state) => state.isIESDSSelected);
  const selectIESDS = useAnalysisStore((state) => state.selectIESDS);

  const currentGameId = useGameStore((state) => state.currentGameId);
  const games = useGameStore((state) => state.games);
  const currentViewMode = useUIStore((state) => state.currentViewMode);
  const isMatrixView = currentViewMode === 'matrix';

  // Get game summary for conversion capabilities
  const gameSummary = games.find((g) => g.id === currentGameId);
  const nativeFormat = gameSummary?.format ?? 'extensive';
  const canConvertToExtensive = gameSummary?.conversions?.extensive?.possible ?? false;

  // Determine what analyses are available based on format and conversions
  const isEfgCapable = nativeFormat === 'extensive' || canConvertToExtensive;
  const isMaidCapable = nativeFormat === 'maid';

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

  // --- IESDS ---
  const handleRunIESDS = () => {
    if (!currentGameId) return;
    runAnalysis(currentGameId, 'iesds');
    setExpandedSections(prev => new Set(prev).add('iesds'));
  };

  // --- MAID Nash Equilibrium ---
  const handleRunMAIDNash = () => {
    if (!currentGameId) return;
    runAnalysis(currentGameId, 'maid-nash');
    setExpandedSections(prev => new Set(prev).add('maid-nash'));
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
  const iesdsResult = resultsByType['iesds'];
  const maidNashResult = resultsByType['maid-nash'];

  return (
    <div className="analysis-panel">
      <h3>Analysis</h3>

      <div className="analysis-sections">
        {/* MAID-specific analyses */}
        {isMaidCapable && (
          <AnalysisSection
            name="MAID Nash"
            description="Compute Nash equilibria for the Multi-Agent Influence Diagram"
            result={maidNashResult}
            isLoading={loadingAnalysis === 'maid-nash'}
            isExpanded={expandedSections.has('maid-nash')}
            selectedIndex={selectedAnalysisId === 'maid-nash' ? selectedIndex : null}
            onToggle={() => toggleSection('maid-nash')}
            onRun={handleRunMAIDNash}
            onCancel={cancelAnalysis}
            onSelectEquilibrium={(index) => selectEquilibrium('maid-nash', index)}
          />
        )}

        {/* EFG/NFG analyses - available if game is or can be converted to EFG */}
        {isEfgCapable && (
          <>
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

            {/* IESDS */}
            <IESDSSection
              result={iesdsResult}
              isLoading={loadingAnalysis === 'iesds'}
              isExpanded={expandedSections.has('iesds')}
              isSelected={isIESDSSelected}
              isMatrixView={isMatrixView}
              onToggle={() => toggleSection('iesds')}
              onRun={handleRunIESDS}
              onCancel={cancelAnalysis}
              onSelect={() => selectIESDS(!isIESDSSelected)}
            />

            <div className="analysis-section">
              <div className="analysis-trigger disabled" title="Check if a strategy profile is an equilibrium">
                <span className="trigger-icon">▶</span>
                <span className="trigger-text">Verify Profile</span>
                <div className="trigger-badges">
                  <span className="coming-soon-badge">Soon</span>
                </div>
              </div>
            </div>
          </>
        )}
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
        {(equilibrium.outcomes || equilibrium.payoffs) && (
          <div className="eq-payoffs">
            <span className="label">Payoffs:</span>
            {Object.entries(equilibrium.outcomes ?? equilibrium.payoffs ?? {}).map(([player, payoff]) => (
              <span key={player} className="payoff">
                {player}: {payoff}
              </span>
            ))}
          </div>
        )}
      </div>
    </button>
  );
}

interface IESDSSectionProps {
  result: { summary: string; details: Record<string, unknown> } | null;
  isLoading: boolean;
  isExpanded: boolean;
  isSelected: boolean;
  isMatrixView: boolean;
  onToggle: () => void;
  onRun: () => void;
  onCancel: () => void;
  onSelect: () => void;
}

interface EliminatedStrategy {
  player: string;
  strategy: string;
  round: number;
}

function IESDSSection({
  result,
  isLoading,
  isExpanded,
  isSelected,
  isMatrixView,
  onToggle,
  onRun,
  onCancel,
  onSelect,
}: IESDSSectionProps) {
  const hasResult = !!result;
  const canExpand = hasResult || isLoading;
  const eliminated = result?.details.eliminated as EliminatedStrategy[] | undefined;
  const surviving = result?.details.surviving as Record<string, string[]> | undefined;
  // Can only click to highlight if in matrix view and has eliminations
  const canHighlight = isMatrixView && (eliminated?.length ?? 0) > 0;
  const rounds = result?.details.rounds as number | undefined;

  const handleHeaderClick = () => {
    if (canExpand) {
      onToggle();
    } else {
      onRun();
    }
  };

  // Count badge - shows eliminated count
  const eliminatedCount = eliminated?.length ?? 0;
  const hasEliminated = eliminatedCount > 0;

  return (
    <div className={`analysis-section ${isExpanded && canExpand ? 'expanded' : ''}`}>
      <div
        className={`analysis-trigger ${hasResult ? 'has-result' : ''}`}
        onClick={handleHeaderClick}
        title="Iteratively Eliminate Strictly Dominated Strategies"
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
        <span className="trigger-text">IESDS</span>

        <div className="trigger-badges">
          {result?.details.computation_time_ms !== undefined && (
            <span className="timing-badge">{result.details.computation_time_ms as number}ms</span>
          )}
          {hasResult && (
            <span className={`count-badge ${eliminatedCount === 0 ? 'none' : ''}`}>
              {eliminatedCount === 0 ? '0' : `-${eliminatedCount}`}
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

          {hasResult && (
            <div className="iesds-result">
              {hasEliminated && (
                <p className="iesds-view-hint">
                  {isMatrixView ? 'Click to highlight on matrix' : 'Switch to matrix view to see visualization'}
                </p>
              )}
              <button
                className={`iesds-card ${isSelected ? 'selected' : ''} ${!canHighlight ? 'disabled' : ''}`}
                onClick={canHighlight ? onSelect : undefined}
                disabled={!canHighlight}
              >
                {eliminated && eliminated.length > 0 ? (
                  <>
                    <p className="iesds-summary">
                      {eliminated.length} strateg{eliminated.length === 1 ? 'y' : 'ies'} eliminated in {rounds} round{rounds !== 1 ? 's' : ''}
                    </p>
                    <div className="eliminated-list">
                      {eliminated.map((e, i) => (
                        <div key={i} className="eliminated-item">
                          <span className="eliminated-round">R{e.round}</span>
                          <span className="eliminated-player">{e.player}</span>
                          <span className="eliminated-strategy">{e.strategy}</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="iesds-summary">No dominated strategies found</p>
                )}

                {surviving && Object.keys(surviving).length > 0 && (
                  <div className="surviving-strategies">
                    <p className="surviving-header">Surviving strategies:</p>
                    {Object.entries(surviving).map(([player, strategies]) => (
                      <div key={player} className="surviving-player">
                        <span className="player-name">{player}:</span>
                        {strategies.map((s) => (
                          <span key={s} className="strategy">{s}</span>
                        ))}
                      </div>
                    ))}
                  </div>
                )}
              </button>

              <div className="analysis-section-footer">
                <span className="rerun-link" onClick={(e) => { e.stopPropagation(); onRun(); }}>
                  Recompute
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
