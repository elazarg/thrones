import { useUIStore } from '../../stores';
import { useGameProperties } from '../../hooks/useGameProperties';
import './StatusBar.css';

interface PropertyChipProps {
  label: string;
  value: boolean | null;
}

function PropertyChip({ label, value }: PropertyChipProps) {
  if (value === null) return null;
  return (
    <span className={`chip property-chip ${value ? 'yes' : 'no'}`}>
      {label}
    </span>
  );
}

export function StatusBar() {
  const openConfig = useUIStore((state) => state.openConfig);
  const properties = useGameProperties();

  return (
    <footer className="status-bar">
      <div className="status-chips">
        <PropertyChip label="2-Player" value={properties.twoPlayer} />
        <PropertyChip label="Zero-Sum" value={properties.zeroSum} />
        <PropertyChip label="Constant-Sum" value={properties.constantSum} />
        <PropertyChip label="Symmetric" value={properties.symmetric} />
        <PropertyChip label="Perfect Info" value={properties.perfectInformation} />
        <PropertyChip label="Deterministic" value={properties.deterministic} />
      </div>
      <button className="config-button" onClick={openConfig}>Configure</button>
    </footer>
  );
}
