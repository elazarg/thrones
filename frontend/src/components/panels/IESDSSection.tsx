export interface IESDSSectionProps {
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

export function IESDSSection({
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
