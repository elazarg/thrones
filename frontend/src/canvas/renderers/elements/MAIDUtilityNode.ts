import { Container, Graphics, TextStyle } from 'pixi.js';
import { createText } from '../../utils/textUtils';
import type { MAIDNodePosition } from '../../layout/maidLayout';
import type { VisualConfig } from '../../config/visualConfig';
import { getPlayerColor } from '../../config/visualConfig';

/**
 * Render a MAID utility node (diamond shape with agent color).
 */
export function renderMAIDUtilityNode(
  container: Container,
  pos: MAIDNodePosition,
  agents: string[],
  config: VisualConfig,
  onHover?: (nodeId: string | null) => void
): void {
  const { maid: maidConfig, node: nodeConfig, text: textConfig } = config;
  const graphics = new Graphics();

  // Determine color based on agent
  const color = pos.agent ? getPlayerColor(pos.agent, agents) : nodeConfig.defaultColor;
  const size = maidConfig.utilityDiamondSize;

  // Draw diamond (rotated square)
  const points = [
    pos.x, pos.y - size,      // top
    pos.x + size, pos.y,      // right
    pos.x, pos.y + size,      // bottom
    pos.x - size, pos.y,      // left
  ];

  graphics
    .poly(points)
    .fill({ color, alpha: maidConfig.utilityFillAlpha })
    .stroke({
      width: nodeConfig.strokeWidth,
      color,
      alpha: 1,
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
