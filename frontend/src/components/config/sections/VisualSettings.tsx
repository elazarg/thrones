import { useConfigStore } from '../../../stores';

export function VisualSettings() {
  const zoomSpeed = useConfigStore((s) => s.zoomSpeed);
  const setZoomSpeed = useConfigStore((s) => s.setZoomSpeed);

  return (
    <div className="config-field">
      <div className="config-field-info">
        <span className="config-field-label">Zoom Speed</span>
        <span className="config-field-hint">Mouse wheel sensitivity</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <input
          type="range"
          className="config-input"
          value={zoomSpeed}
          min={0.05}
          max={0.5}
          step={0.01}
          onChange={(e) => setZoomSpeed(parseFloat(e.target.value))}
        />
        <span className="zoom-value">{Math.round(zoomSpeed * 100)}%</span>
      </div>
    </div>
  );
}
