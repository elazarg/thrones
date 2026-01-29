import { useAnalysisStore, useUIStore } from '../../stores';
import './StatusBar.css';

export function StatusBar() {
  const resultsByType = useAnalysisStore((state) => state.resultsByType);
  const loadingAnalysis = useAnalysisStore((state) => state.loadingAnalysis);
  const openConfig = useUIStore((state) => state.openConfig);

  // Get non-null results
  const results = Object.entries(resultsByType)
    .filter(([, result]) => result !== null)
    .map(([id, result]) => ({ id, ...result! }));

  return (
    <footer className="status-bar">
      <div className="status-chips">
        {loadingAnalysis && <span className="chip loading">Computing...</span>}
        {results.map((result) => (
          <span key={result.id} className="chip">
            {result.summary}
          </span>
        ))}
      </div>
      <button className="config-button" onClick={openConfig}>Configure</button>
    </footer>
  );
}
