import { Container, Graphics, TextStyle } from 'pixi.js';
import { createText } from '../../utils/textUtils';
import type { MatrixCell } from '../../layout/matrixLayout';
import type { VisualConfig } from '../../config/visualConfig';

/**
 * Render a single cell in the payoff matrix.
 */
export function renderMatrixCell(
  container: Container,
  cell: MatrixCell,
  config: VisualConfig,
  options?: {
    isEquilibrium?: boolean;
    isDominated?: [boolean, boolean];
  }
): void {
  const graphics = new Graphics();
  const { x, y, width, height, payoffs } = cell;
  const isEquilibrium = options?.isEquilibrium ?? false;
  const isDominated = options?.isDominated ?? [false, false];

  // Cell background
  const bgColor = isEquilibrium ? 0x1a1a2e : 0x161b22;
  graphics.rect(x, y, width, height).fill({ color: bgColor });

  // Cell border
  const borderColor = isEquilibrium ? 0xffd700 : 0x30363d;
  const borderWidth = isEquilibrium ? 2 : 1;
  graphics.rect(x, y, width, height).stroke({ color: borderColor, width: borderWidth });

  container.addChild(graphics);

  // Payoff text - format as "P1, P2" with player colors
  const p1Color = config.playerColors[0];
  const p2Color = config.playerColors[1];

  // P1 payoff (row player)
  const p1Alpha = isDominated[0] ? 0.4 : 1;
  const p1Style = new TextStyle({
    fontFamily: config.text.fontFamily,
    fontSize: 14,
    fill: p1Color,
    fontWeight: 'bold',
  });
  const p1Text = createText({
    text: formatPayoff(payoffs[0]),
    style: p1Style,
  });
  p1Text.anchor.set(1, 0.5); // Right-align
  p1Text.x = x + width / 2 - 4;
  p1Text.y = y + height / 2;
  p1Text.alpha = p1Alpha;
  container.addChild(p1Text);

  // Comma separator
  const commaStyle = new TextStyle({
    fontFamily: config.text.fontFamily,
    fontSize: 14,
    fill: 0x8b949e,
  });
  const commaText = createText({
    text: ',',
    style: commaStyle,
  });
  commaText.anchor.set(0.5, 0.5);
  commaText.x = x + width / 2;
  commaText.y = y + height / 2;
  container.addChild(commaText);

  // P2 payoff (column player)
  const p2Alpha = isDominated[1] ? 0.4 : 1;
  const p2Style = new TextStyle({
    fontFamily: config.text.fontFamily,
    fontSize: 14,
    fill: p2Color,
    fontWeight: 'bold',
  });
  const p2Text = createText({
    text: formatPayoff(payoffs[1]),
    style: p2Style,
  });
  p2Text.anchor.set(0, 0.5); // Left-align
  p2Text.x = x + width / 2 + 4;
  p2Text.y = y + height / 2;
  p2Text.alpha = p2Alpha;
  container.addChild(p2Text);
}

/**
 * Format a payoff number for display.
 */
function formatPayoff(value: number): string {
  // Show integers without decimals, otherwise show 1 decimal place
  if (Number.isInteger(value)) {
    return value.toString();
  }
  return value.toFixed(1);
}
