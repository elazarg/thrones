import { useAnalysisStore, useUIStore } from '../../stores';
import { isAnalysisError } from '../../types';
import './StatusBar.css';

export function StatusBar() {
  const resultsByType = useAnalysisStore((state) => state.resultsByType);
  const loadingAnalysis = useAnalysisStore((state) => state.loadingAnalysis);
  const openConfig = useUIStore((state) => state.openConfig);

  // Get non-null, non-error results (errors are shown in the analysis section)
  const results = Object.entries(resultsByType)
    .filter(([, result]) => result !== null && !isAnalysisError(result))
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
