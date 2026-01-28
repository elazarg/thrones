import { Container, Graphics, TextStyle } from 'pixi.js';
import { createText } from '../../utils/textUtils';
import type { MAIDNodePosition } from '../../layout/maidLayout';
import type { VisualConfig } from '../../config/visualConfig';

/**
 * Render a MAID chance node (hexagon shape, neutral gray).
 */
export function renderMAIDChanceNode(
  container: Container,
  pos: MAIDNodePosition,
  config: VisualConfig,
  onHover?: (nodeId: string | null) => void
): void {
  const { maid: maidConfig, node: nodeConfig, text: textConfig } = config;
  const graphics = new Graphics();

  const size = maidConfig.chanceHexagonSize;
  const color = maidConfig.chanceColor;

  // Draw hexagon (6 points)
  const points: number[] = [];
  for (let i = 0; i < 6; i++) {
    // Start from top point, rotate 60 degrees each time
    const angle = (Math.PI / 2) + (i * Math.PI / 3);
    points.push(pos.x + size * Math.cos(angle));
    points.push(pos.y - size * Math.sin(angle));
  }

  graphics
    .poly(points)
    .fill({ color, alpha: nodeConfig.fillAlpha })
    .stroke({
      width: nodeConfig.strokeWidth,
      color: nodeConfig.strokeColor,
      alpha: nodeConfig.strokeAlpha,
    });

  // Make interactive
  graphics.eventMode = 'static';
  graphics.cursor = 'pointer';
  if (onHover) {
    graphics.on('pointerover', () => onHover(pos.id));
    graphics.on('pointerout', () => onHover(null));
  }

  container.addChild(graphics);

  // Node ID label below
  const labelStyle = new TextStyle({
    fontFamily: textConfig.fontFamily,
    fontSize: 10,
    fill: 0x8b949e,
  });
  const label = createText({ text: pos.label, style: labelStyle });
  label.anchor.set(0.5, 0);
  label.x = pos.x;
  label.y = pos.y + size + 4;
  container.addChild(label);
}
