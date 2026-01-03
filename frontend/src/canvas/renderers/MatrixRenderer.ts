import { Container } from 'pixi.js';
import type { MatrixLayout } from '../layout/matrixLayout';
import type { VisualConfig } from '../config/visualConfig';
import type { NormalFormGame } from '../../types';
import { renderMatrixCell } from './elements/MatrixCell';
import { renderMatrixHeader, renderPlayerLabel } from './elements/MatrixHeader';

/**
 * Context passed to the matrix renderer.
 */
export interface MatrixRenderContext {
  config: VisualConfig;
  equilibriumCells?: Set<string>; // Set of "row,col" strings for equilibrium cells
  dominatedRows?: Set<number>; // Indices of dominated rows (P1 strategies)
  dominatedCols?: Set<number>; // Indices of dominated columns (P2 strategies)
}

/**
 * MatrixRenderer renders normal form games as payoff matrices.
 */
export class MatrixRenderer {
  /**
   * Render the entire matrix to the given container.
   */
  render(
    container: Container,
    _game: NormalFormGame,
    layout: MatrixLayout,
    context: MatrixRenderContext
  ): void {
    const { config, equilibriumCells, dominatedRows, dominatedCols } = context;

    // 1. Render player labels
    this.renderPlayerLabels(container, layout, config);

    // 2. Render headers
    this.renderHeaders(container, layout, config, dominatedRows, dominatedCols);

    // 3. Render cells
    this.renderCells(container, layout, config, equilibriumCells, dominatedRows, dominatedCols);
  }

  /**
   * Render player name labels.
   */
  private renderPlayerLabels(
    container: Container,
    layout: MatrixLayout,
    config: VisualConfig
  ): void {
    // Row player (P1) - on the left, rotated
    renderPlayerLabel(
      container,
      layout.rowPlayerLabel.x,
      layout.rowPlayerLabel.y,
      layout.rowPlayerLabel.text,
      0,
      config,
      true // vertical
    );

    // Column player (P2) - on top
    renderPlayerLabel(
      container,
      layout.colPlayerLabel.x,
      layout.colPlayerLabel.y,
      layout.colPlayerLabel.text,
      1,
      config,
      false // horizontal
    );
  }

  /**
   * Render row and column headers.
   */
  private renderHeaders(
    container: Container,
    layout: MatrixLayout,
    config: VisualConfig,
    dominatedRows?: Set<number>,
    dominatedCols?: Set<number>
  ): void {
    // Row headers (P1 strategies)
    for (const header of layout.rowHeaders) {
      const isDominated = dominatedRows?.has(header.index) ?? false;
      renderMatrixHeader(container, header, config, { isDominated });
    }

    // Column headers (P2 strategies)
    for (const header of layout.colHeaders) {
      const isDominated = dominatedCols?.has(header.index) ?? false;
      renderMatrixHeader(container, header, config, { isDominated });
    }
  }

  /**
   * Render all cells.
   */
  private renderCells(
    container: Container,
    layout: MatrixLayout,
    config: VisualConfig,
    equilibriumCells?: Set<string>,
    dominatedRows?: Set<number>,
    dominatedCols?: Set<number>
  ): void {
    for (const row of layout.cells) {
      for (const cell of row) {
        const cellKey = `${cell.row},${cell.col}`;
        const isEquilibrium = equilibriumCells?.has(cellKey) ?? false;
        const isDominated: [boolean, boolean] = [
          dominatedRows?.has(cell.row) ?? false,
          dominatedCols?.has(cell.col) ?? false,
        ];

        renderMatrixCell(container, cell, config, {
          isEquilibrium,
          isDominated,
        });
      }
    }
  }

  /**
   * Clear all rendered content from the container.
   */
  clear(container: Container): void {
    container.removeChildren();
  }
}

// Singleton instance for convenience
export const matrixRenderer = new MatrixRenderer();
