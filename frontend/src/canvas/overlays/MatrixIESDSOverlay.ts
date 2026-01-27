import { Container, Graphics, TextStyle } from 'pixi.js';
import { createText } from '../utils/textUtils';
import type { MatrixOverlay, MatrixOverlayContext } from './types';
import type { VisualConfig } from '../config/visualConfig';

/** Unique label for matrix IESDS overlay container */
const OVERLAY_LABEL = '__matrix_iesds_overlay__';

/**
 * Data for matrix IESDS overlay.
 */
interface MatrixIESDSOverlayData {
  eliminatedRows: Array<{
    index: number;
    x: number;
    y: number;
    width: number;
    height: number;
    strategy: string;
    round: number;
  }>;
  eliminatedCols: Array<{
    index: number;
    x: number;
    y: number;
    width: number;
    height: number;
    strategy: string;
    round: number;
  }>;
  survivingRows: Array<{
    index: number;
    x: number;
    y: number;
    width: number;
    height: number;
  }>;
  survivingCols: Array<{
    index: number;
    x: number;
    y: number;
    width: number;
    height: number;
  }>;
}

/**
 * Overlay that shows IESDS results on the payoff matrix.
 * Highlights eliminated strategies with strikethrough and surviving strategies with green.
 */
export class MatrixIESDSOverlay implements MatrixOverlay {
  id = 'matrix-iesds';
  zIndex = 90; // Below equilibrium overlay

  compute(context: MatrixOverlayContext): MatrixIESDSOverlayData | null {
    const { selectedIESDSResult, layout, game } = context;

    if (!selectedIESDSResult) {
      return null;
    }

    const { eliminated, surviving } = selectedIESDSResult;
    const [player1, player2] = game.players;

    // Find eliminated row strategies (player 1)
    const eliminatedRows: MatrixIESDSOverlayData['eliminatedRows'] = [];
    for (let row = 0; row < layout.rowStrategies.length; row++) {
      const strategy = layout.rowStrategies[row];
      const elimInfo = eliminated.find(e => e.player === player1 && e.strategy === strategy);
      if (elimInfo) {
        const header = layout.rowHeaders[row];
        eliminatedRows.push({
          index: row,
          x: header.x,
          y: header.y,
          width: header.width,
          height: header.height,
          strategy,
          round: elimInfo.round,
        });
      }
    }

    // Find eliminated column strategies (player 2)
    const eliminatedCols: MatrixIESDSOverlayData['eliminatedCols'] = [];
    for (let col = 0; col < layout.colStrategies.length; col++) {
      const strategy = layout.colStrategies[col];
      const elimInfo = eliminated.find(e => e.player === player2 && e.strategy === strategy);
      if (elimInfo) {
        const header = layout.colHeaders[col];
        eliminatedCols.push({
          index: col,
          x: header.x,
          y: header.y,
          width: header.width,
          height: header.height,
          strategy,
          round: elimInfo.round,
        });
      }
    }

    // Find surviving row strategies
    const survivingRows: MatrixIESDSOverlayData['survivingRows'] = [];
    const survivingP1 = surviving[player1] || [];
    for (let row = 0; row < layout.rowStrategies.length; row++) {
      const strategy = layout.rowStrategies[row];
      if (survivingP1.includes(strategy)) {
        const header = layout.rowHeaders[row];
        survivingRows.push({
          index: row,
          x: header.x,
          y: header.y,
          width: header.width,
          height: header.height,
        });
      }
    }

    // Find surviving column strategies
    const survivingCols: MatrixIESDSOverlayData['survivingCols'] = [];
    const survivingP2 = surviving[player2] || [];
    for (let col = 0; col < layout.colStrategies.length; col++) {
      const strategy = layout.colStrategies[col];
      if (survivingP2.includes(strategy)) {
        const header = layout.colHeaders[col];
        survivingCols.push({
          index: col,
          x: header.x,
          y: header.y,
          width: header.width,
          height: header.height,
        });
      }
    }

    return { eliminatedRows, eliminatedCols, survivingRows, survivingCols };
  }

  apply(container: Container, data: unknown, config: VisualConfig): void {
    const overlayData = data as MatrixIESDSOverlayData;

    const overlayContainer = new Container();
    overlayContainer.label = OVERLAY_LABEL;
    overlayContainer.zIndex = this.zIndex;

    const eliminatedColor = 0xf85149; // Red
    const survivingColor = 0x3fb950; // Green
    const strikethroughWidth = 2;

    // Draw eliminated row strategies (strikethrough + red border)
    for (const row of overlayData.eliminatedRows) {
      const graphics = new Graphics();

      // Red border on header
      graphics
        .rect(row.x, row.y, row.width, row.height)
        .stroke({ color: eliminatedColor, width: 2, alpha: 0.7 });

      // Strikethrough line
      graphics
        .moveTo(row.x + 4, row.y + row.height / 2)
        .lineTo(row.x + row.width - 4, row.y + row.height / 2)
        .stroke({ color: eliminatedColor, width: strikethroughWidth, alpha: 0.9 });

      overlayContainer.addChild(graphics);

      // Round badge
      const badgeStyle = new TextStyle({
        fontFamily: config.text.fontFamily,
        fontSize: 8,
        fill: 0xffffff,
        fontWeight: 'bold',
      });
      const badge = createText({
        text: `R${row.round}`,
        style: badgeStyle,
      });
      badge.anchor.set(1, 0);
      badge.x = row.x + row.width - 2;
      badge.y = row.y + 2;

      // Badge background
      const badgeBg = new Graphics();
      badgeBg
        .roundRect(badge.x - badge.width - 4, badge.y - 1, badge.width + 6, badge.height + 2, 3)
        .fill({ color: eliminatedColor, alpha: 0.9 });
      overlayContainer.addChild(badgeBg);
      overlayContainer.addChild(badge);
    }

    // Draw eliminated column strategies (strikethrough + red border)
    for (const col of overlayData.eliminatedCols) {
      const graphics = new Graphics();

      // Red border on header
      graphics
        .rect(col.x, col.y, col.width, col.height)
        .stroke({ color: eliminatedColor, width: 2, alpha: 0.7 });

      // Strikethrough line (vertical for column headers)
      graphics
        .moveTo(col.x + col.width / 2, col.y + 4)
        .lineTo(col.x + col.width / 2, col.y + col.height - 4)
        .stroke({ color: eliminatedColor, width: strikethroughWidth, alpha: 0.9 });

      overlayContainer.addChild(graphics);

      // Round badge
      const badgeStyle = new TextStyle({
        fontFamily: config.text.fontFamily,
        fontSize: 8,
        fill: 0xffffff,
        fontWeight: 'bold',
      });
      const badge = createText({
        text: `R${col.round}`,
        style: badgeStyle,
      });
      badge.anchor.set(0.5, 1);
      badge.x = col.x + col.width / 2;
      badge.y = col.y + col.height - 2;

      // Badge background
      const badgeBg = new Graphics();
      badgeBg
        .roundRect(badge.x - badge.width / 2 - 3, badge.y - badge.height - 1, badge.width + 6, badge.height + 2, 3)
        .fill({ color: eliminatedColor, alpha: 0.9 });
      overlayContainer.addChild(badgeBg);
      overlayContainer.addChild(badge);
    }

    // Draw surviving row strategies (green border)
    for (const row of overlayData.survivingRows) {
      const graphics = new Graphics();
      graphics
        .rect(row.x, row.y, row.width, row.height)
        .stroke({ color: survivingColor, width: 2, alpha: 0.8 });
      graphics
        .rect(row.x + 2, row.y + 2, row.width - 4, row.height - 4)
        .fill({ color: survivingColor, alpha: 0.1 });
      overlayContainer.addChild(graphics);
    }

    // Draw surviving column strategies (green border)
    for (const col of overlayData.survivingCols) {
      const graphics = new Graphics();
      graphics
        .rect(col.x, col.y, col.width, col.height)
        .stroke({ color: survivingColor, width: 2, alpha: 0.8 });
      graphics
        .rect(col.x + 2, col.y + 2, col.width - 4, col.height - 4)
        .fill({ color: survivingColor, alpha: 0.1 });
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

export const matrixIESDSOverlay = new MatrixIESDSOverlay();
