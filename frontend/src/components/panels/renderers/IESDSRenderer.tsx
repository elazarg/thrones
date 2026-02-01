import type { AnalysisSectionResult } from '../../../types';
import { isEliminatedStrategyArray, isSurvivingStrategies } from '../../../types';

export interface IESDSRendererProps {
  result: AnalysisSectionResult;
  isSelected: boolean;
  isMatrixView: boolean;
  onSelect: () => void;
}

export function IESDSRenderer({
  result,
  isSelected,
  isMatrixView,
  onSelect,
}: IESDSRendererProps) {
  const rawEliminated = result?.details.eliminated;
  const eliminated = isEliminatedStrategyArray(rawEliminated) ? rawEliminated : undefined;
  const rawSurviving = result?.details.surviving;
  const surviving = isSurvivingStrategies(rawSurviving) ? rawSurviving : undefined;
  const rawRounds = result?.details.rounds;
  const rounds = typeof rawRounds === 'number' ? rawRounds : undefined;

  // Can only click to highlight if in matrix view and has eliminations
  const canHighlight = isMatrixView && (eliminated?.length ?? 0) > 0;
  const hasEliminated = (eliminated?.length ?? 0) > 0;

  return (
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
    </div>
  );
}
