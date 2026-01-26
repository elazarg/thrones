import { useMemo } from 'react';
import type { ExtensiveFormGame } from '../../types';
import { calculateLayout, TreeLayout } from '../layout/treeLayout';

/**
 * Hook that computes the tree layout for a game.
 * Memoized to avoid recalculation unless the game changes.
 */
export function useLayout(game: ExtensiveFormGame | null): TreeLayout | null {
  return useMemo(() => {
    if (!game) return null;
    return calculateLayout(game);
  }, [game]);
}
