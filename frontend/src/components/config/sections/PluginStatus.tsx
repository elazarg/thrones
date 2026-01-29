import { useEffect, useState } from 'react';

interface PluginInfo {
  name: string;
  healthy: boolean;
  port: number | null;
  analyses: string[];
}

export function PluginStatus() {
  const [plugins, setPlugins] = useState<PluginInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchStatus() {
      try {
        const res = await fetch('/api/plugins/status');
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        if (!cancelled) {
          setPlugins(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to fetch');
          setPlugins(null);
        }
      }
    }

    fetchStatus();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return <div className="plugin-error">Failed to load plugin status: {error}</div>;
  }

  if (!plugins) {
    return <div className="plugin-loading">Loading...</div>;
  }

  if (plugins.length === 0) {
    return <div className="plugin-loading">No plugins configured</div>;
  }

  return (
    <div className="plugin-list">
      {plugins.map((plugin) => (
        <div key={plugin.name} className="plugin-item">
          <div className={`plugin-status-dot ${plugin.healthy ? 'healthy' : 'unhealthy'}`} />
          <span className="plugin-name">{plugin.name}</span>
          <span className="plugin-status-text">
            {plugin.healthy ? `Running on port ${plugin.port}` : 'Not running'}
          </span>
        </div>
      ))}
    </div>
  );
}
