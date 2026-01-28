import type { NashEquilibrium } from '../../types';
import { toFraction } from '../../utils/mathUtils';

interface EquilibriumCardProps {
  equilibrium: NashEquilibrium;
  index: number;
  isSelected: boolean;
  onSelect: () => void;
}

export function EquilibriumCard({ equilibrium, index, isSelected, onSelect }: EquilibriumCardProps) {
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
