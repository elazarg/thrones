/**
 * Matrix layout engine for normal form games.
 * Computes cell positions for rendering payoff matrices.
 */
import type { NormalFormGame } from '../../types';

/**
 * A cell in the payoff matrix.
 */
export interface MatrixCell {
  row: number;
  col: number;
  x: number;
  y: number;
  width: number;
  height: number;
  payoffs: [number, number]; // [P1 payoff, P2 payoff]
}

/**
 * A header label (row or column).
 */
export interface MatrixHeader {
  index: number;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  isRow: boolean; // true for row headers (P1), false for column headers (P2)
}

/**
 * Complete matrix layout with all positions computed.
 */
export interface MatrixLayout {
  // Dimensions
  width: number;
  height: number;
  cellWidth: number;
  cellHeight: number;

  // Player info
  players: [string, string];
  rowStrategies: string[]; // P1 strategies
  colStrategies: string[]; // P2 strategies

  // Positioned elements
  cells: MatrixCell[][];
  rowHeaders: MatrixHeader[];
  colHeaders: MatrixHeader[];

  // Player label positions
  rowPlayerLabel: { x: number; y: number; text: string };
  colPlayerLabel: { x: number; y: number; text: string };
}

/**
 * Default matrix layout configuration.
 * Can be overridden by visualConfig when implemented.
 */
const DEFAULT_CONFIG = {
  cellWidth: 80,
  cellHeight: 50,
  headerWidth: 80,
  headerHeight: 30,
  playerLabelMargin: 10,
  padding: 40,
};

/**
 * Calculate the layout for a normal form game matrix.
 */
export function calculateMatrixLayout(game: NormalFormGame): MatrixLayout {
  const config = DEFAULT_CONFIG;

  const numRows = game.strategies[0].length;
  const numCols = game.strategies[1].length;

  // Calculate dimensions
  const gridWidth = numCols * config.cellWidth;
  const gridHeight = numRows * config.cellHeight;

  // Grid starts after headers
  const gridStartX = config.headerWidth + config.padding;
  const gridStartY = config.headerHeight + config.padding;

  // Total dimensions
  const totalWidth = gridStartX + gridWidth + config.padding;
  const totalHeight = gridStartY + gridHeight + config.padding + config.playerLabelMargin;

  // Create cells
  const cells: MatrixCell[][] = [];
  for (let row = 0; row < numRows; row++) {
    const rowCells: MatrixCell[] = [];
    for (let col = 0; col < numCols; col++) {
      rowCells.push({
        row,
        col,
        x: gridStartX + col * config.cellWidth,
        y: gridStartY + row * config.cellHeight,
        width: config.cellWidth,
        height: config.cellHeight,
        payoffs: game.payoffs[row][col],
      });
    }
    cells.push(rowCells);
  }

  // Create row headers (P1 strategies)
  const rowHeaders: MatrixHeader[] = game.strategies[0].map((label, index) => ({
    index,
    label,
    x: config.padding,
    y: gridStartY + index * config.cellHeight,
    width: config.headerWidth,
    height: config.cellHeight,
    isRow: true,
  }));

  // Create column headers (P2 strategies)
  const colHeaders: MatrixHeader[] = game.strategies[1].map((label, index) => ({
    index,
    label,
    x: gridStartX + index * config.cellWidth,
    y: config.padding,
    width: config.cellWidth,
    height: config.headerHeight,
    isRow: false,
  }));

  // Player label positions
  const rowPlayerLabel = {
    x: config.padding / 2,
    y: gridStartY + gridHeight / 2,
    text: game.players[0],
  };

  const colPlayerLabel = {
    x: gridStartX + gridWidth / 2,
    y: config.padding / 2,
    text: game.players[1],
  };

  return {
    width: totalWidth,
    height: totalHeight,
    cellWidth: config.cellWidth,
    cellHeight: config.cellHeight,
    players: game.players,
    rowStrategies: game.strategies[0],
    colStrategies: game.strategies[1],
    cells,
    rowHeaders,
    colHeaders,
    rowPlayerLabel,
    colPlayerLabel,
  };
}
