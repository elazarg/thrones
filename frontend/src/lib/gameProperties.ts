import {
  type AnyGame,
  type NormalFormGame,
  type ExtensiveFormGame,
  isNormalFormGame,
  isExtensiveFormGame,
} from '../types';

const EPSILON = 1e-9;

// --- NFG property checks ---

export function isZeroSumNFG(game: NormalFormGame): boolean {
  for (const row of game.payoffs) {
    for (const [p1, p2] of row) {
      if (Math.abs(p1 + p2) > EPSILON) return false;
    }
  }
  return true;
}

export function isConstantSumNFG(game: NormalFormGame): boolean {
  let firstSum: number | null = null;
  for (const row of game.payoffs) {
    for (const [p1, p2] of row) {
      const sum = p1 + p2;
      if (firstSum === null) {
        firstSum = sum;
      } else if (Math.abs(sum - firstSum) > EPSILON) {
        return false;
      }
    }
  }
  return true;
}

export function isSymmetricNFG(game: NormalFormGame): boolean {
  const [s1, s2] = game.strategies;
  if (s1.length !== s2.length) return false;

  const n = s1.length;
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      const [p1_ij, p2_ij] = game.payoffs[i][j];
      const [p1_ji, p2_ji] = game.payoffs[j][i];
      if (Math.abs(p1_ij - p2_ji) > EPSILON) return false;
      if (Math.abs(p2_ij - p1_ji) > EPSILON) return false;
    }
  }
  return true;
}

// --- EFG property checks ---

export function isZeroSumEFG(game: ExtensiveFormGame): boolean {
  for (const outcome of Object.values(game.outcomes)) {
    const sum = Object.values(outcome.payoffs).reduce((a, b) => a + b, 0);
    if (Math.abs(sum) > EPSILON) return false;
  }
  return true;
}

export function isConstantSumEFG(game: ExtensiveFormGame): boolean {
  let firstSum: number | null = null;
  for (const outcome of Object.values(game.outcomes)) {
    const sum = Object.values(outcome.payoffs).reduce((a, b) => a + b, 0);
    if (firstSum === null) {
      firstSum = sum;
    } else if (Math.abs(sum - firstSum) > EPSILON) {
      return false;
    }
  }
  return true;
}

export function hasPerfectInformation(game: ExtensiveFormGame): boolean {
  const infoSetCounts = new Map<string, number>();
  for (const node of Object.values(game.nodes)) {
    if (node.information_set) {
      const count = (infoSetCounts.get(node.information_set) || 0) + 1;
      if (count > 1) return false;
      infoSetCounts.set(node.information_set, count);
    }
  }
  return true;
}

export function isDeterministicEFG(game: ExtensiveFormGame): boolean {
  for (const node of Object.values(game.nodes)) {
    const playerLower = node.player.toLowerCase();
    if (playerLower === 'chance' || playerLower === 'nature') {
      return false;
    }
    for (const action of node.actions) {
      if (action.probability !== undefined) {
        return false;
      }
    }
  }
  return true;
}

// --- Generic property computation from any game that has the right format ---

export function computeZeroSum(game: AnyGame): boolean | null {
  if (isNormalFormGame(game)) return isZeroSumNFG(game);
  if (isExtensiveFormGame(game)) return isZeroSumEFG(game);
  return null;
}

export function computeConstantSum(game: AnyGame): boolean | null {
  if (isNormalFormGame(game)) return isConstantSumNFG(game);
  if (isExtensiveFormGame(game)) return isConstantSumEFG(game);
  return null;
}

export function computeSymmetric(game: AnyGame): boolean | null {
  if (isNormalFormGame(game)) return isSymmetricNFG(game);
  return null;
}

export function computePerfectInformation(game: AnyGame): boolean | null {
  if (isExtensiveFormGame(game)) return hasPerfectInformation(game);
  return null;
}

export function computeDeterministic(game: AnyGame): boolean | null {
  if (isExtensiveFormGame(game)) return isDeterministicEFG(game);
  return null;
}
