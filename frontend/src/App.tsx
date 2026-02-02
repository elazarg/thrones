import { useEffect, useRef } from 'react';
import { useGameStore, useAnalysisStore } from './stores';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Header } from './components/layout/Header';
import { GameInfoBar } from './components/layout/GameInfoBar';
import { StatusBar } from './components/layout/StatusBar';
import { MainLayout } from './components/layout/MainLayout';
import { ConfigModal } from './components/config/ConfigModal';

export default function App() {
  const fetchGames = useGameStore((state) => state.fetchGames);
  const currentGameId = useGameStore((state) => state.currentGameId);
  const gamesError = useGameStore((state) => state.gamesError);
  const gameError = useGameStore((state) => state.gameError);

  const clearAnalyses = useAnalysisStore((state) => state.clear);

  // Track previous game ID for cleanup
  const prevGameIdRef = useRef<string | null>(null);

  // Fetch games list on mount
  useEffect(() => {
    fetchGames();
  }, [fetchGames]);

  // Clear analyses when game changes (user will manually trigger analysis)
  useEffect(() => {
    if (prevGameIdRef.current !== currentGameId) {
      // Game changed - clear previous analysis results
      clearAnalyses();
      prevGameIdRef.current = currentGameId;
    }
  }, [currentGameId, clearAnalyses]);

  // Only show full-screen error for critical failures (game list/data loading)
  // Analysis errors are shown locally in AnalysisSection
  const error = gamesError || gameError;

  if (error) {
    return (
      <div className="app error-state">
        <pre>{error}</pre>
      </div>
    );
  }

  return (
    <ErrorBoundary name="App">
      <div className="app">
        <Header />
        <GameInfoBar />
        <ErrorBoundary name="MainLayout">
          <MainLayout />
        </ErrorBoundary>
        <StatusBar />
      </div>
      <ConfigModal />
    </ErrorBoundary>
  );
}
