import type { AnalysisSectionResult } from '../../../types';
import { isNashEquilibriumArray } from '../../../types';
import { EquilibriumCard } from '../EquilibriumCard';

export interface EquilibriumRendererProps {
  result: AnalysisSectionResult;
  selectedIndex: number | null;
  onSelectEquilibrium: (index: number | null) => void;
}

export function EquilibriumRenderer({
  result,
  selectedIndex,
  onSelectEquilibrium,
}: EquilibriumRendererProps) {
  const rawEquilibria = result?.details.equilibria;
  const equilibria = isNashEquilibriumArray(rawEquilibria) ? rawEquilibria : undefined;

  if (!equilibria) {
    // No equilibria data - show summary text
    return (
      <div className="analysis-result-text">
        {result?.summary}
      </div>
    );
  }

  return (
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
    </div>
  );
}

