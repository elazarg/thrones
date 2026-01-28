import { Container, Graphics, TextStyle } from 'pixi.js';
import { createText } from '../../utils/textUtils';
import type { MAIDNodePosition } from '../../layout/maidLayout';
import type { VisualConfig } from '../../config/visualConfig';
import { getPlayerColor } from '../../config/visualConfig';

/**
 * Render a MAID decision node (circle with agent label).
 */
export function renderMAIDDecisionNode(
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

  // Draw circle
  graphics
    .circle(pos.x, pos.y, maidConfig.decisionRadius)
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

  // Agent label inside node
  if (pos.agent) {
    const style = new TextStyle({
      fontFamily: textConfig.fontFamily,
      fontSize: textConfig.playerLabel.size,
      fill: textConfig.playerLabel.color,
      fontWeight: textConfig.playerLabel.weight,
    });
    const text = createText({ text: pos.agent, style });
    text.anchor.set(0.5, 0.5);
    text.x = pos.x;
    text.y = pos.y;
    container.addChild(text);
  }

  // Node ID label below
  const labelStyle = new TextStyle({
    fontFamily: textConfig.fontFamily,
    fontSize: 10,
    fill: 0x8b949e,
  });
  const label = createText({ text: pos.label, style: labelStyle });
  label.anchor.set(0.5, 0);
  label.x = pos.x;
  label.y = pos.y + maidConfig.decisionRadius + 4;
  container.addChild(label);
}
