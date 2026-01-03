import { Container, Graphics } from 'pixi.js';
import type { MatrixOverlay, MatrixOverlayContext } from './types';
import type { VisualConfig } from '../config/visualConfig';

/** Unique label for matrix equilibrium overlay container */
const OVERLAY_LABEL = '__matrix_equilibrium_overlay__';

/**
 * Data for matrix equilibrium overlay - cells to highlight.
 */
interface MatrixEquilibriumOverlayData {
  cells: Array<{
    row: number;
    col: number;
    x: number;
    y: number;
    width: number;
    height: number;
    probability: number; // 1.0 for pure, < 1 for mixed
  }>;
}

/**
 * Get the probability of a strategy being played in an equilibrium.
 * Returns 0 if the strategy is not in the profile.
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
 * Overlay that highlights equilibrium cells in the payoff matrix.
 * For pure equilibria, highlights the single cell.
 * For mixed equilibria, highlights cells with probability > 0.
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
    const { strategies } = selectedEquilibrium;

    // Get player names
    const [player1, player2] = game.players;

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

    return cells.length > 0 ? { cells } : null;
  }

  apply(container: Container, data: unknown, config: VisualConfig): void {
    const overlayData = data as MatrixEquilibriumOverlayData;

    // Create overlay container
    const overlayContainer = new Container();
    overlayContainer.label = OVERLAY_LABEL;
    overlayContainer.zIndex = this.zIndex;

    const borderColor = config.equilibrium?.borderColor ?? 0xffd700; // Gold
    const borderWidth = 3;

    for (const cell of overlayData.cells) {
      const graphics = new Graphics();

      // Draw highlight border around cell
      // Use alpha based on probability for mixed equilibria
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
    }

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
