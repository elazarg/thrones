import { Container, Graphics, TextStyle } from 'pixi.js';
import { createText } from '../utils/textUtils';
import { toFraction } from '../../utils/mathUtils';
import { clearOverlayByLabel } from './overlayUtils';
import type { MatrixOverlay, MatrixOverlayContext } from './types';
import type { VisualConfig } from '../config/visualConfig';
import type { NormalFormGame } from '../../types';

/** Unique label for matrix equilibrium overlay container */
const OVERLAY_LABEL = '__matrix_equilibrium_overlay__';

/**
 * Data for matrix equilibrium overlay.
 */
interface MatrixEquilibriumOverlayData {
  cells: Array<{
    row: number;
    col: number;
    x: number;
    y: number;
    width: number;
    height: number;
    probability: number;
  }>;
  rowProbabilities: Array<{ index: number; x: number; y: number; width: number; height: number; probability: number }>;
  colProbabilities: Array<{ index: number; x: number; y: number; width: number; height: number; probability: number }>;
  playerPayoffs: {
    row: { x: number; y: number; payoff: number; playerName: string };
    col: { x: number; y: number; payoff: number; playerName: string };
  };
  isMixed: boolean;
}

/**
 * Get the probability of a strategy being played in an equilibrium.
 */
function getStrategyProbability(
  strategies: Record<string, Record<string, number>>,
  playerName: string,
  strategyName: string
): number {
  const playerStrategies = strategies[playerName];
  if (!playerStrategies) return 0;
  return playerStrategies[strategyName] ?? 0;
}

/**
 * Normalize MAID equilibrium to NFG format.
 * MAID equilibria have behavior_profile keyed by decision node ID.
 * NFG equilibria need strategies keyed by player name.
 *
 * Handles compound strategies (like "C/C") that arise when a player has
 * multiple nodes in an information set. The MAID action "C" maps to "C/C"
 * if all parts of the compound strategy are the same action.
 */
function normalizeMAIDEquilibriumToNFG(
  equilibrium: { behavior_profile?: Record<string, Record<string, number>>; strategies?: Record<string, Record<string, number>> },
  maidDecisionToPlayer: Record<string, string>,
  nfgStrategies: [string[], string[]],
  players: [string, string]
): Record<string, Record<string, number>> {
  const behaviorProfile = equilibrium.behavior_profile || equilibrium.strategies;
  if (!behaviorProfile) return {};

  const result: Record<string, Record<string, number>> = {};

  for (const [nodeId, actions] of Object.entries(behaviorProfile)) {
    const player = maidDecisionToPlayer[nodeId];
    if (!player) continue;

    // Get the NFG strategies for this player
    const playerIndex = players.indexOf(player);
    const playerNfgStrategies = playerIndex >= 0 ? nfgStrategies[playerIndex] : [];

    // Initialize player's strategies if not yet present
    if (!result[player]) {
      result[player] = {};
    }

    // Copy action probabilities as strategy probabilities
    for (const [action, prob] of Object.entries(actions)) {
      // Try to find matching NFG strategy
      // 1. Direct match (simple case)
      if (playerNfgStrategies.includes(action)) {
        result[player][action] = (result[player][action] ?? 0) + prob;
      } else {
        // 2. Compound strategy match (e.g., "C" matches "C/C")
        // Find strategies where all parts are the same action
        for (const nfgStrategy of playerNfgStrategies) {
          const parts = nfgStrategy.split('/');
          if (parts.length > 0 && parts.every(p => p === action)) {
            result[player][nfgStrategy] = (result[player][nfgStrategy] ?? 0) + prob;
            break;
          }
        }
      }
    }
  }

  return result;
}

/**
 * Compute expected payoffs from a strategy profile and NFG payoff matrix.
 */
function computePayoffsFromProfile(
  game: NormalFormGame,
  strategies: Record<string, Record<string, number>>
): Record<string, number> {
  const [player1, player2] = game.players;
  const [p1Strategies, p2Strategies] = game.strategies;

  let p1Payoff = 0;
  let p2Payoff = 0;

  for (let row = 0; row < p1Strategies.length; row++) {
    const rowStrategy = p1Strategies[row];
    const p1Prob = strategies[player1]?.[rowStrategy] ?? 0;
    if (p1Prob <= 0) continue;

    for (let col = 0; col < p2Strategies.length; col++) {
      const colStrategy = p2Strategies[col];
      const p2Prob = strategies[player2]?.[colStrategy] ?? 0;
      if (p2Prob <= 0) continue;

      const cellProb = p1Prob * p2Prob;
      const [cellP1, cellP2] = game.payoffs[row][col];
      p1Payoff += cellProb * cellP1;
      p2Payoff += cellProb * cellP2;
    }
  }

  return { [player1]: p1Payoff, [player2]: p2Payoff };
}

/**
 * Overlay that highlights equilibrium cells in the payoff matrix.
 * Shows strategy probabilities, cell probabilities, and expected payoffs.
 */
export class MatrixEquilibriumOverlay implements MatrixOverlay {
  id = 'matrix-equilibrium';
  zIndex = 100;

  compute(context: MatrixOverlayContext): MatrixEquilibriumOverlayData | null {
    const { selectedEquilibrium, layout, game } = context;

    if (!selectedEquilibrium) {
      return null;
    }

    const cells: MatrixEquilibriumOverlayData['cells'] = [];
    let { strategies, payoffs } = selectedEquilibrium;

    // Get player names
    const [player1, player2] = game.players;

    // Check if this is a MAID equilibrium that needs normalization
    // MAID equilibria have behavior_profile keyed by decision node ID (e.g., "D1", "D2")
    // NFG equilibria have strategies keyed by player name
    const maidDecisionToPlayer = (game as { maid_decision_to_player?: Record<string, string> }).maid_decision_to_player;
    if (maidDecisionToPlayer && Object.keys(maidDecisionToPlayer).length > 0) {
      const behaviorProfile = selectedEquilibrium.behavior_profile || strategies;
      if (behaviorProfile) {
        // Check if keys are decision node IDs (present in mapping) rather than player names
        const firstKey = Object.keys(behaviorProfile)[0];
        if (firstKey && maidDecisionToPlayer[firstKey]) {
          // This is a MAID equilibrium - normalize it to NFG format
          strategies = normalizeMAIDEquilibriumToNFG(
            selectedEquilibrium,
            maidDecisionToPlayer,
            game.strategies,
            game.players
          );

          // For MAID equilibria, compute payoffs from the NFG if not present
          if (!payoffs) {
            payoffs = computePayoffsFromProfile(game, strategies);
          }
        }
      }
    }

    // Skip if still no strategies after normalization attempt
    if (!strategies || Object.keys(strategies).length === 0) {
      return null;
    }

    // Ensure payoffs is defined - compute from strategies if necessary
    if (!payoffs) {
      payoffs = computePayoffsFromProfile(game, strategies);
    }

    // Check if this is a mixed equilibrium
    const allProbs = Object.values(strategies).flatMap(s => Object.values(s));
    const isMixed = allProbs.some(p => p > 0.001 && p < 0.999);

    // Collect row probabilities (player 1 strategies)
    const rowProbabilities: MatrixEquilibriumOverlayData['rowProbabilities'] = [];
    for (let row = 0; row < layout.rowStrategies.length; row++) {
      const prob = getStrategyProbability(strategies, player1, layout.rowStrategies[row]);
      const header = layout.rowHeaders[row];
      rowProbabilities.push({
        index: row,
        x: header.x,
        y: header.y,
        width: header.width,
        height: header.height,
        probability: prob,
      });
    }

    // Collect column probabilities (player 2 strategies)
    const colProbabilities: MatrixEquilibriumOverlayData['colProbabilities'] = [];
    for (let col = 0; col < layout.colStrategies.length; col++) {
      const prob = getStrategyProbability(strategies, player2, layout.colStrategies[col]);
      const header = layout.colHeaders[col];
      colProbabilities.push({
        index: col,
        x: header.x,
        y: header.y,
        width: header.width,
        height: header.height,
        probability: prob,
      });
    }

    // For each cell, check if it's part of the equilibrium support
    for (let row = 0; row < layout.rowStrategies.length; row++) {
      for (let col = 0; col < layout.colStrategies.length; col++) {
        const rowStrategy = layout.rowStrategies[row];
        const colStrategy = layout.colStrategies[col];

        const p1Prob = getStrategyProbability(strategies, player1, rowStrategy);
        const p2Prob = getStrategyProbability(strategies, player2, colStrategy);

        // Cell is in equilibrium support if both strategies have positive probability
        const cellProb = p1Prob * p2Prob;

        if (cellProb > 0.001) {
          const cell = layout.cells[row][col];
          cells.push({
            row,
            col,
            x: cell.x,
            y: cell.y,
            width: cell.width,
            height: cell.height,
            probability: cellProb,
          });
        }
      }
    }

    // Player payoff positions (below player labels, not overlapping)
    // Row player label is rotated, so we position payoff below the grid on the left
    // Col player label is horizontal, so we position payoff to the right of the label
    const lastRow = layout.rowHeaders[layout.rowHeaders.length - 1];
    const lastCol = layout.colHeaders[layout.colHeaders.length - 1];

    const playerPayoffs = {
      row: {
        x: layout.rowPlayerLabel.x,
        y: lastRow.y + lastRow.height + 15, // Below the last row header
        payoff: payoffs[player1] ?? 0,
        playerName: player1,
      },
      col: {
        x: lastCol.x + lastCol.width + 15, // Right of the last column header
        y: layout.colPlayerLabel.y,
        payoff: payoffs[player2] ?? 0,
        playerName: player2,
      },
    };

    return { cells, rowProbabilities, colProbabilities, playerPayoffs, isMixed };
  }

  apply(container: Container, data: unknown, config: VisualConfig): void {
    const overlayData = data as MatrixEquilibriumOverlayData;

    // Create overlay container
    const overlayContainer = new Container();
    overlayContainer.label = OVERLAY_LABEL;
    overlayContainer.zIndex = this.zIndex;

    const borderColor = config.equilibrium?.borderColor ?? 0xffd700; // Gold
    const borderWidth = 3;

    // Draw cell highlights
    for (const cell of overlayData.cells) {
      const graphics = new Graphics();
      const alpha = Math.max(0.5, cell.probability);

      graphics
        .rect(cell.x, cell.y, cell.width, cell.height)
        .stroke({
          color: borderColor,
          width: borderWidth,
          alpha,
        });

      // For pure equilibria (prob = 1), add a subtle inner glow
      if (cell.probability > 0.99) {
        graphics
          .rect(
            cell.x + borderWidth,
            cell.y + borderWidth,
            cell.width - borderWidth * 2,
            cell.height - borderWidth * 2
          )
          .fill({
            color: borderColor,
            alpha: 0.1,
          });
      }

      overlayContainer.addChild(graphics);

      // Show cell probability for mixed equilibria
      if (overlayData.isMixed && cell.probability < 0.99) {
        const probStyle = new TextStyle({
          fontFamily: config.text.fontFamily,
          fontSize: 9,
          fill: borderColor,
          fontWeight: 'bold',
        });
        const probText = createText({
          text: toFraction(cell.probability),
          style: probStyle,
        });
        probText.anchor.set(1, 0);
        probText.x = cell.x + cell.width - 3;
        probText.y = cell.y + 2;
        overlayContainer.addChild(probText);
      }
    }

    // Show strategy probabilities on row headers (for mixed equilibria)
    if (overlayData.isMixed) {
      for (const row of overlayData.rowProbabilities) {
        if (row.probability > 0.001) {
          const probStyle = new TextStyle({
            fontFamily: config.text.fontFamily,
            fontSize: 10,
            fill: borderColor,
            fontWeight: 'bold',
          });
          const probText = createText({
            text: toFraction(row.probability),
            style: probStyle,
          });
          probText.anchor.set(1, 0.5);
          probText.x = row.x + row.width - 4;
          probText.y = row.y + row.height / 2;
          overlayContainer.addChild(probText);
        }
      }

      // Show strategy probabilities on column headers
      for (const col of overlayData.colProbabilities) {
        if (col.probability > 0.001) {
          const probStyle = new TextStyle({
            fontFamily: config.text.fontFamily,
            fontSize: 10,
            fill: borderColor,
            fontWeight: 'bold',
          });
          const probText = createText({
            text: toFraction(col.probability),
            style: probStyle,
          });
          probText.anchor.set(0.5, 1);
          probText.x = col.x + col.width / 2;
          probText.y = col.y + col.height - 2;
          overlayContainer.addChild(probText);
        }
      }
    }

    // Show expected payoffs near player areas
    const payoffStyle = new TextStyle({
      fontFamily: config.text.fontFamily,
      fontSize: 10,
      fill: borderColor,
    });

    // Row player payoff (below the grid, left side)
    const rowPayoffText = createText({
      text: `E[${overlayData.playerPayoffs.row.playerName}] = ${overlayData.playerPayoffs.row.payoff}`,
      style: payoffStyle,
    });
    rowPayoffText.anchor.set(0, 0.5);
    rowPayoffText.x = overlayData.playerPayoffs.row.x;
    rowPayoffText.y = overlayData.playerPayoffs.row.y;
    overlayContainer.addChild(rowPayoffText);

    // Column player payoff (right of the grid, top)
    const colPayoffText = createText({
      text: `E[${overlayData.playerPayoffs.col.playerName}] = ${overlayData.playerPayoffs.col.payoff}`,
      style: payoffStyle,
    });
    colPayoffText.anchor.set(0, 0.5);
    colPayoffText.x = overlayData.playerPayoffs.col.x;
    colPayoffText.y = overlayData.playerPayoffs.col.y;
    overlayContainer.addChild(colPayoffText);

    container.addChild(overlayContainer);
  }

  clear(container: Container): void {
    clearOverlayByLabel(container, OVERLAY_LABEL);
  }
}

// Singleton instance
export const matrixEquilibriumOverlay = new MatrixEquilibriumOverlay();
