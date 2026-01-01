import { useEffect } from 'react';
import { useGameStore, useAnalysisStore } from './stores';
import { Header } from './components/layout/Header';
import { StatusBar } from './components/layout/StatusBar';
import { MainLayout } from './components/layout/MainLayout';

export default function App() {
  const fetchGame = useGameStore((state) => state.fetchGame);
  const fetchAnalyses = useAnalysisStore((state) => state.fetchAnalyses);
  const gameError = useGameStore((state) => state.error);
  const analysisError = useAnalysisStore((state) => state.error);

  useEffect(() => {
    fetchGame();
    fetchAnalyses();
  }, [fetchGame, fetchAnalyses]);

  const error = gameError || analysisError;

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
