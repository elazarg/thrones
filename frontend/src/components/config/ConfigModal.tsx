import { Modal } from '../common/Modal';
import { useUIStore, useConfigStore } from '../../stores';
import { AnalysisSettings } from './sections/AnalysisSettings';
import { VisualSettings } from './sections/VisualSettings';
import { PluginStatus } from './sections/PluginStatus';
import './ConfigModal.css';

export function ConfigModal() {
  const isOpen = useUIStore((s) => s.isConfigOpen);
  const closeConfig = useUIStore((s) => s.closeConfig);
  const resetToDefaults = useConfigStore((s) => s.resetToDefaults);

  return (
    <Modal
      isOpen={isOpen}
      onClose={closeConfig}
      title="Configuration"
      footer={
        <>
          <button className="config-reset-btn" onClick={resetToDefaults}>
            Reset to Defaults
          </button>
          <button onClick={closeConfig}>Close</button>
        </>
      }
    >
      <section className="config-section">
        <h3 className="config-section-title">Analysis Defaults</h3>
        <AnalysisSettings />
      </section>

      <section className="config-section">
        <h3 className="config-section-title">Visual Preferences</h3>
        <VisualSettings />
      </section>

      <section className="config-section">
        <h3 className="config-section-title">Plugin Status</h3>
        <PluginStatus />
      </section>
    </Modal>
  );
}
