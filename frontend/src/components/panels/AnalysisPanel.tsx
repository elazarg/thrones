import { useState } from 'react';
import { useAnalysisStore, useGameStore, useUIStore, useConfigStore } from '../../stores';
import { AnalysisSection } from './AnalysisSection';
import { IESDSSection } from './IESDSSection';
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
  const currentViewFormat = useUIStore((state) => state.currentViewFormat);
  const isMatrixView = currentViewFormat === 'matrix';
  const defaultMaxEquilibria = useConfigStore((state) => state.defaultMaxEquilibria);

  // Get game summary for conversion capabilities
  const gameSummary = games.find((g) => g.id === currentGameId);
  const nativeFormat = gameSummary?.format ?? 'extensive';
  const canConvertToExtensive = gameSummary?.conversions?.extensive?.possible ?? false;

  // Determine what analyses are available based on format and conversions
  const isEfgCapable = nativeFormat === 'extensive' || canConvertToExtensive;
  const isMaidCapable = nativeFormat === 'maid';

  // Track which sections are expanded
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  // Track current max_equilibria for the NE backoff (uses config default as starting point)
  const [neMaxEquilibria, setNeMaxEquilibria] = useState(defaultMaxEquilibria);

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

  // --- MAID Subgame Perfect Equilibrium ---
  const handleRunMAIDSPE = () => {
    if (!currentGameId) return;
    runAnalysis(currentGameId, 'maid-spe');
    setExpandedSections(prev => new Set(prev).add('maid-spe'));
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
  const maidSpeResult = resultsByType['maid-spe'];

  return (
    <div className="analysis-panel">
      <h3>Analysis</h3>

      <div className="analysis-sections">
        {/* MAID-specific analyses */}
        {isMaidCapable && (
          <>
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
            <AnalysisSection
              name="MAID SPE"
              description="Compute subgame perfect equilibria for the MAID"
              result={maidSpeResult}
              isLoading={loadingAnalysis === 'maid-spe'}
              isExpanded={expandedSections.has('maid-spe')}
              selectedIndex={selectedAnalysisId === 'maid-spe' ? selectedIndex : null}
              onToggle={() => toggleSection('maid-spe')}
              onRun={handleRunMAIDSPE}
              onCancel={cancelAnalysis}
              onSelectEquilibrium={(index) => selectEquilibrium('maid-spe', index)}
            />
          </>
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
              onRun={() => handleRunNE(defaultMaxEquilibria)}
              onCancel={cancelAnalysis}
              onSelectEquilibrium={(index) => selectEquilibrium('nash', index)}
              extraFooter={
                nashResult && !nashResult.details.exhaustive ? (
                  <button type="button" className="rerun-link" onClick={(e) => { e.stopPropagation(); handleFindMoreNE(); }}>
                    Find more (up to {neMaxEquilibria * 2})
                  </button>
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
