import { Container, Graphics, TextStyle } from 'pixi.js';
import { createText } from '../utils/textUtils';
import type { MatrixOverlay, MatrixOverlayContext } from './types';
import type { VisualConfig } from '../config/visualConfig';

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
 * Convert a decimal probability to a simple fraction string.
 * Handles common fractions like 1/2, 1/3, 1/4, etc.
 */
function toFraction(decimal: number): string {
  if (decimal === 0) return '0';
  if (decimal === 1) return '1';

  // Common denominators to try
  const denominators = [2, 3, 4, 5, 6, 8, 10, 12];

  for (const d of denominators) {
    const n = Math.round(decimal * d);
    if (Math.abs(n / d - decimal) < 0.0001) {
      // Simplify the fraction
      const gcd = (a: number, b: number): number => b === 0 ? a : gcd(b, a % b);
      const g = gcd(n, d);
      const num = n / g;
      const den = d / g;
      if (den === 1) return `${num}`;
      return `${num}/${den}`;
    }
  }

  // Fall back to decimal with 2 places
  return decimal.toFixed(2);
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
    const { strategies, payoffs } = selectedEquilibrium;

    // Get player names
    const [player1, player2] = game.players;

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
    const overlayContainer = container.children.find(
      (child) => child.label === OVERLAY_LABEL
    );
    if (overlayContainer) {
      container.removeChild(overlayContainer);
      overlayContainer.destroy({ children: true });
    }
  }
}

// Singleton instance
export const matrixEquilibriumOverlay = new MatrixEquilibriumOverlay();
