import { useAnalysisStore } from '../../stores';
import './StatusBar.css';

export function StatusBar() {
  const results = useAnalysisStore((state) => state.results);
  const loading = useAnalysisStore((state) => state.loading);

  return (
    <footer className="status-bar">
      <div className="status-chips">
        {loading && <span className="chip loading">Loading...</span>}
        {results.map((result, index) => (
          <span key={index} className="chip">
            {result.summary}
          </span>
        ))}
      </div>
      <button className="config-button" disabled>Configure</button>
    </footer>
  );
}
