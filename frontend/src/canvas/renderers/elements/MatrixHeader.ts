import { Container, Graphics, Text, TextStyle } from 'pixi.js';
import type { MatrixHeader } from '../../layout/matrixLayout';
import type { VisualConfig } from '../../config/visualConfig';

/**
 * Render a strategy header (row or column).
 */
export function renderMatrixHeader(
  container: Container,
  header: MatrixHeader,
  config: VisualConfig,
  options?: {
    isDominated?: boolean;
  }
): void {
  const { x, y, width, height, label } = header;
  const isDominated = options?.isDominated ?? false;

  const graphics = new Graphics();

  // Header background
  const bgColor = 0x21262d;
  graphics.rect(x, y, width, height).fill({ color: bgColor });

  // Border
  graphics.rect(x, y, width, height).stroke({ color: 0x30363d, width: 1 });

  container.addChild(graphics);

  // Strategy label
  const textColor = isDominated ? 0x6e7681 : 0xc9d1d9;
  const labelStyle = new TextStyle({
    fontFamily: config.text.fontFamily,
    fontSize: 12,
    fill: textColor,
    fontStyle: isDominated ? 'italic' : 'normal',
  });

  const labelText = new Text({
    text: label,
    style: labelStyle,
  });
  labelText.anchor.set(0.5, 0.5);
  labelText.x = x + width / 2;
  labelText.y = y + height / 2;
  labelText.alpha = isDominated ? 0.6 : 1;
  container.addChild(labelText);
}

/**
 * Render a player name label.
 */
export function renderPlayerLabel(
  container: Container,
  x: number,
  y: number,
  label: string,
  playerIndex: number,
  config: VisualConfig,
  isVertical: boolean = false
): void {
  const playerColor = config.playerColors[playerIndex % config.playerColors.length];

  const labelStyle = new TextStyle({
    fontFamily: config.text.fontFamily,
    fontSize: 11,
    fill: playerColor,
    fontWeight: 'bold',
  });

  const labelText = new Text({
    text: label,
    style: labelStyle,
  });
  labelText.anchor.set(0.5, 0.5);
  labelText.x = x;
  labelText.y = y;

  if (isVertical) {
    labelText.rotation = -Math.PI / 2;
  }

  container.addChild(labelText);
}
