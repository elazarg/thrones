import { Container, Graphics, TextStyle } from 'pixi.js';
import { createText } from '../../utils/textUtils';
import type { NodePosition } from '../../layout/treeLayout';
import type { VisualConfig } from '../../config/visualConfig';
import { getPlayerColor } from '../../config/visualConfig';

/**
 * Render a decision node (circle with player label).
 */
export function renderDecisionNode(
  container: Container,
  nodeId: string,
  pos: NodePosition,
  players: string[],
  config: VisualConfig,
  onHover?: (nodeId: string | null) => void
): void {
  const { node: nodeConfig, text: textConfig } = config;
  const graphics = new Graphics();

  // Determine color
  const color = pos.player ? getPlayerColor(pos.player, players) : nodeConfig.defaultColor;

  // Draw circle
  graphics
    .circle(pos.x, pos.y, nodeConfig.decisionRadius)
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
    graphics.on('pointerover', () => onHover(nodeId));
    graphics.on('pointerout', () => onHover(null));
  }

  container.addChild(graphics);

  // Player label
  if (pos.player) {
    const style = new TextStyle({
      fontFamily: textConfig.fontFamily,
      fontSize: textConfig.playerLabel.size,
      fill: textConfig.playerLabel.color,
      fontWeight: textConfig.playerLabel.weight,
    });
    const text = createText({ text: pos.player, style });
    text.anchor.set(0.5, 0.5);
    text.x = pos.x;
    text.y = pos.y;
    container.addChild(text);
  }
}
