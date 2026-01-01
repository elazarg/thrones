import { useEffect } from 'react';
import { useGameStore, useAnalysisStore } from './stores';
import { Header } from './components/layout/Header';
import { StatusBar } from './components/layout/StatusBar';
import { MainLayout } from './components/layout/MainLayout';

export default function App() {
  const fetchGames = useGameStore((state) => state.fetchGames);
  const currentGameId = useGameStore((state) => state.currentGameId);
  const gamesError = useGameStore((state) => state.gamesError);
  const gameError = useGameStore((state) => state.gameError);

  const fetchAnalyses = useAnalysisStore((state) => state.fetchAnalyses);
  const clearAnalyses = useAnalysisStore((state) => state.clear);
  const analysisError = useAnalysisStore((state) => state.error);

  // Fetch games list on mount
  useEffect(() => {
    fetchGames();
  }, [fetchGames]);

  // Fetch analyses when game changes
  useEffect(() => {
    if (currentGameId) {
      fetchAnalyses(currentGameId);
    } else {
      clearAnalyses();
    }
  }, [currentGameId, fetchAnalyses, clearAnalyses]);

  const error = gamesError || gameError || analysisError;

  if (error) {
    return (
      <div className="app error-state">
        <pre>{error}</pre>
      </div>
    );
  }

  return (
    <div className="app">
      <Header />
      <MainLayout />
      <StatusBar />
    </div>
  );
}
