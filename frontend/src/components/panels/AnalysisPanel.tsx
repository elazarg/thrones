import { useState, useEffect } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { useAnalysisStore, useGameStore, useUIStore, useConfigStore, usePluginStore } from '../../stores';
import { getApplicableAnalyses, getRegistryEntry } from '../../registry/analysisRegistry';
import { BaseAnalysisSection } from './BaseAnalysisSection';
import { VegasPanel } from './VegasPanel';
import { EquilibriumRenderer } from './renderers/EquilibriumRenderer';
import { IESDSRenderer } from './renderers/IESDSRenderer';
import { ExploitabilityRenderer } from './renderers/ExploitabilityRenderer';
import { ReplicatorDynamicsRenderer } from './renderers/ReplicatorDynamicsRenderer';
import { EvolutionaryStabilityRenderer } from './renderers/EvolutionaryStabilityRenderer';
import { CFRConvergenceRenderer } from './renderers/CFRConvergenceRenderer';
import { DecisionRelevanceRenderer } from './renderers/DecisionRelevanceRenderer';
import { FictitiousPlayRenderer } from './renderers/FictitiousPlayRenderer';
import './AnalysisPanel.css';

interface AnalysisPanelProps {
  onSelectCompiledTab?: (targetId: string) => void;
}

export function AnalysisPanel({ onSelectCompiledTab }: AnalysisPanelProps) {
  const {
    resultsByType,
    loadingAnalysis,
    selectedIndex,
    selectedAnalysisId,
    selectEquilibrium,
    runAnalysis,
    cancelAnalysis,
    isIESDSSelected,
    selectIESDS,
  } = useAnalysisStore(
    useShallow((state) => ({
      resultsByType: state.resultsByType,
      loadingAnalysis: state.loadingAnalysis,
      selectedIndex: state.selectedEquilibriumIndex,
      selectedAnalysisId: state.selectedAnalysisId,
      selectEquilibrium: state.selectEquilibrium,
      runAnalysis: state.runAnalysis,
      cancelAnalysis: state.cancelAnalysis,
      isIESDSSelected: state.isIESDSSelected,
      selectIESDS: state.selectIESDS,
    }))
  );

  const { currentGameId, games } = useGameStore(
    useShallow((state) => ({
      currentGameId: state.currentGameId,
      games: state.games,
    }))
  );
  const currentViewFormat = useUIStore((state) => state.currentViewFormat);
  const isMatrixView = currentViewFormat === 'matrix';
  const { defaultMaxEquilibria, analysisTimeout } = useConfigStore(
    useShallow((state) => ({
      defaultMaxEquilibria: state.defaultMaxEquilibria,
      analysisTimeout: state.analysisTimeout,
    }))
  );

  // Get game summary for conversion capabilities
  const gameSummary = games.find((g) => g.id === currentGameId);
  const nativeFormat = gameSummary?.format ?? 'extensive';
  const canConvertToExtensive = gameSummary?.conversions?.extensive?.possible ?? false;
  const canConvertToNormal = gameSummary?.conversions?.normal?.possible ?? false;
  const canConvertToMaid = gameSummary?.conversions?.maid?.possible ?? false;

  // Determine what analyses are available based on format and conversions
  const isEfgCapable = nativeFormat === 'extensive' || canConvertToExtensive;
  const isNfgCapable = nativeFormat === 'normal' || canConvertToNormal;
  const isMaidCapable = nativeFormat === 'maid' || canConvertToMaid;

  // Fetch analysis applicability when game changes
  const { fetchApplicability, applicabilityByGame, loadingApplicability } = usePluginStore(
    useShallow((state) => ({
      fetchApplicability: state.fetchApplicability,
      applicabilityByGame: state.applicabilityByGame,
      loadingApplicability: state.loadingApplicability,
    }))
  );

  useEffect(() => {
    if (currentGameId) {
      fetchApplicability(currentGameId);
    }
  }, [currentGameId, fetchApplicability]);

  // Helper to get applicability for an analysis
  const getAnalysisApplicability = (analysisName: string | undefined) => {
    if (!analysisName || !currentGameId) return { applicable: true };

    const isLoading = !!loadingApplicability[currentGameId];
    const gameApplicability = applicabilityByGame[currentGameId];

    if (isLoading || !gameApplicability) {
      return { applicable: false, loading: true, reason: 'Checking...' };
    }
    return gameApplicability[analysisName] || { applicable: true };
  };

  // Track which sections are expanded
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  // Track current max_equilibria for the NE backoff
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

  // Generic run handler
  const handleRun = (analysisId: string, options?: { maxEquilibria?: number }) => {
    if (!currentGameId) return;
    const entry = getRegistryEntry(analysisId);
    const finalOptions = { ...entry?.defaultOptions, ...options, timeout: analysisTimeout };
    runAnalysis(currentGameId, analysisId, finalOptions);
    setExpandedSections(prev => new Set(prev).add(analysisId));
  };

  // Special handler for Nash with backoff
  const handleRunNash = (maxEq: number) => {
    setNeMaxEquilibria(maxEq);
    handleRun('nash', { maxEquilibria: maxEq });
  };

  const handleFindMoreNE = () => {
    const nextMax = neMaxEquilibria * 2;
    handleRunNash(nextMax);
  };

  // Check if current game is Vegas format
  const isVegas = nativeFormat === 'vegas';

  if (!currentGameId) {
    return (
      <div className="analysis-panel">
        <h3>Analysis</h3>
        <p className="empty">Select a game to analyze</p>
      </div>
    );
  }

  // Get applicable analyses based on game format
  const applicableAnalyses = getApplicableAnalyses(isEfgCapable, isNfgCapable, isMaidCapable);

  // Render content based on analysis type
  const renderAnalysisContent = (analysisId: string) => {
    const result = resultsByType[analysisId];

    // Equilibrium-based analyses (Nash, SPE, Backward Induction)
    if (['pure-ne', 'nash', 'approx-ne', 'maid-nash', 'maid-spe', 'backward-induction'].includes(analysisId)) {
      return (
        <EquilibriumRenderer
          result={result}
          selectedIndex={selectedAnalysisId === analysisId ? selectedIndex : null}
          onSelectEquilibrium={(index) => selectEquilibrium(analysisId, index)}
        />
      );
    }

    // IESDS (strict and weak)
    if (analysisId === 'iesds' || analysisId === 'weak-iesds') {
      return (
        <IESDSRenderer
          result={result}
          isSelected={isIESDSSelected}
          isMatrixView={isMatrixView}
          onSelect={() => selectIESDS(!isIESDSSelected)}
        />
      );
    }

    // Exploitability
    if (analysisId === 'exploitability') {
      return <ExploitabilityRenderer result={result} />;
    }

    // CFR Convergence
    if (analysisId === 'cfr-convergence') {
      return <CFRConvergenceRenderer result={result} />;
    }

    // Fictitious Play
    if (analysisId === 'fictitious-play') {
      return <FictitiousPlayRenderer result={result} />;
    }

    // Decision Relevance (MAID)
    if (analysisId === 'decision-relevance') {
      return <DecisionRelevanceRenderer result={result} />;
    }

    // Replicator Dynamics
    if (analysisId === 'replicator-dynamics') {
      return <ReplicatorDynamicsRenderer result={result} />;
    }

    // Evolutionary Stability
    if (analysisId === 'evolutionary-stability') {
      return <EvolutionaryStabilityRenderer result={result} />;
    }

    // Fallback - show summary
    return (
      <div className="analysis-result-text">
        {result?.summary}
      </div>
    );
  };

  // Render extra footer for nash backoff
  const renderNashExtraFooter = () => {
    const nashResult = resultsByType['nash'];
    if (nashResult && !nashResult.details.exhaustive) {
      return (
        <button
          type="button"
          className="rerun-link"
          onClick={(e) => {
            e.stopPropagation();
            handleFindMoreNE();
          }}
        >
          Find more (up to {neMaxEquilibria * 2})
        </button>
      );
    }
    return null;
  };

  return (
    <div className="analysis-panel">
      {/* Vegas panel for compilation - only for Vegas games */}
      {isVegas && onSelectCompiledTab && (
        <VegasPanel onSelectCompiledTab={onSelectCompiledTab} />
      )}

      <h3>Analysis</h3>

      <div className="analysis-sections">
        {applicableAnalyses.map((entry) => {
          const result = resultsByType[entry.id];
          const applicability = getAnalysisApplicability(entry.applicabilityKey);
          const isDisabled = entry.applicabilityKey ? !applicability.applicable : false;

          return (
            <BaseAnalysisSection
              key={entry.id}
              analysisId={entry.id}
              name={entry.name}
              description={entry.description}
              result={result}
              isLoading={loadingAnalysis === entry.id}
              isExpanded={expandedSections.has(entry.id)}
              disabled={isDisabled}
              disabledReason={applicability.reason}
              onToggle={() => toggleSection(entry.id)}
              onRun={() => {
                if (entry.id === 'nash') {
                  handleRunNash(defaultMaxEquilibria);
                } else {
                  handleRun(entry.id);
                }
              }}
              onCancel={cancelAnalysis}
              loadingText={entry.loadingText}
              renderBadge={() => entry.renderBadge?.(result)}
              renderContent={() => renderAnalysisContent(entry.id)}
              renderExtraFooter={entry.id === 'nash' ? renderNashExtraFooter : undefined}
            />
          );
        })}

        {/* Placeholder for future "Verify Profile" feature - only show for EFG capable games */}
        {isEfgCapable && (
          <div className="analysis-section">
            <div className="analysis-trigger disabled" title="Check if a strategy profile is an equilibrium">
              <span className="trigger-icon">▶</span>
              <span className="trigger-text">Verify Profile</span>
              <div className="trigger-badges">
                <span className="coming-soon-badge">Soon</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
