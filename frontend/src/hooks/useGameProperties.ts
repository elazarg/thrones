import { useEffect, useState, useMemo } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { useGameStore } from '../stores';
import {
  type AnyGame,
  type GameSummary,
  isNormalFormGame,
  isExtensiveFormGame,
  isMAIDGame,
} from '../types';
import {
  computeZeroSum,
  computeConstantSum,
  computeSymmetric,
  computePerfectInformation,
  computeDeterministic,
} from '../lib/gameProperties';

export interface GameProperties {
  twoPlayer: boolean | null;
  zeroSum: boolean | null;
  constantSum: boolean | null;
  symmetric: boolean | null;
  perfectInformation: boolean | null;
  deterministic: boolean | null;
}

type ConvertibleFormat = 'extensive' | 'normal';

/**
 * Check if a format is available (either native or via conversion).
 */
function isFormatAvailable(
  nativeGame: AnyGame | null,
  summary: GameSummary | null,
  format: ConvertibleFormat
): boolean {
  if (!nativeGame) return false;

  // Check if native format matches
  if (format === 'normal' && isNormalFormGame(nativeGame)) return true;
  if (format === 'extensive' && isExtensiveFormGame(nativeGame)) return true;

  // Check if conversion is possible
  const conversionInfo = summary?.conversions?.[format];
  return conversionInfo?.possible === true;
}

/**
 * Get a game in the requested format (native or converted).
 */
function getGameInFormat(
  nativeGame: AnyGame | null,
  convertedGames: Map<ConvertibleFormat, AnyGame | null>,
  format: ConvertibleFormat
): AnyGame | null {
  if (!nativeGame) return null;

  // Return native if it matches
  if (format === 'normal' && isNormalFormGame(nativeGame)) return nativeGame;
  if (format === 'extensive' && isExtensiveFormGame(nativeGame)) return nativeGame;

  // Return converted
  return convertedGames.get(format) ?? null;
}

/**
 * Get player count from any game type.
 */
function getPlayerCount(game: AnyGame): number {
  if (isMAIDGame(game)) return game.agents.length;
  return game.players.length;
}

/**
 * Hook that computes game properties, fetching conversions as needed.
 */
export function useGameProperties(): GameProperties {
  const { currentGame, currentGameId, games, fetchConverted } = useGameStore(
    useShallow((s) => ({
      currentGame: s.currentGame,
      currentGameId: s.currentGameId,
      games: s.games,
      fetchConverted: s.fetchConverted,
    }))
  );

  // Get the summary for conversion info
  const summary = useMemo(
    () => games.find((g) => g.id === currentGameId) ?? null,
    [games, currentGameId]
  );

  // Track converted games
  const [convertedGames, setConvertedGames] = useState<Map<ConvertibleFormat, AnyGame | null>>(
    new Map()
  );

  // Determine which formats we need
  const needsNormal = useMemo(
    () =>
      isFormatAvailable(currentGame, summary, 'normal') &&
      currentGame !== null &&
      !isNormalFormGame(currentGame),
    [currentGame, summary]
  );

  const needsExtensive = useMemo(
    () =>
      isFormatAvailable(currentGame, summary, 'extensive') &&
      currentGame !== null &&
      !isExtensiveFormGame(currentGame),
    [currentGame, summary]
  );

  // Fetch conversions when needed
  useEffect(() => {
    if (!currentGameId) {
      setConvertedGames(new Map());
      return;
    }

    const fetchNeeded = async () => {
      const newConverted = new Map<ConvertibleFormat, AnyGame | null>();

      if (needsNormal) {
        const normalGame = await fetchConverted(currentGameId, 'normal');
        newConverted.set('normal', normalGame);
      }

      if (needsExtensive) {
        const extensiveGame = await fetchConverted(currentGameId, 'extensive');
        newConverted.set('extensive', extensiveGame);
      }

      setConvertedGames(newConverted);
    };

    fetchNeeded();
  }, [currentGameId, needsNormal, needsExtensive, fetchConverted]);

  // Compute properties
  return useMemo(() => {
    const nullProps: GameProperties = {
      twoPlayer: null,
      zeroSum: null,
      constantSum: null,
      symmetric: null,
      perfectInformation: null,
      deterministic: null,
    };

    if (!currentGame) return nullProps;

    // Player count - available from any game
    const twoPlayer = getPlayerCount(currentGame) === 2;

    // Get games in needed formats
    const normalGame = getGameInFormat(currentGame, convertedGames, 'normal');
    const extensiveGame = getGameInFormat(currentGame, convertedGames, 'extensive');

    // Compute properties from whichever format is available
    // For zero-sum and constant-sum, prefer NFG if available (simpler), else EFG
    const zeroSum = normalGame
      ? computeZeroSum(normalGame)
      : extensiveGame
        ? computeZeroSum(extensiveGame)
        : null;

    const constantSum = normalGame
      ? computeConstantSum(normalGame)
      : extensiveGame
        ? computeConstantSum(extensiveGame)
        : null;

    // Symmetric requires NFG
    const symmetric = normalGame ? computeSymmetric(normalGame) : null;

    // Perfect information and deterministic require EFG
    const perfectInformation = extensiveGame ? computePerfectInformation(extensiveGame) : null;
    const deterministic = extensiveGame ? computeDeterministic(extensiveGame) : null;

    return {
      twoPlayer,
      zeroSum,
      constantSum,
      symmetric,
      perfectInformation,
      deterministic,
    };
  }, [currentGame, convertedGames]);
}
