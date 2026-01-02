import { Container, Graphics, Text, TextStyle } from 'pixi.js';
import type { NodePosition } from '../../layout/treeLayout';
import type { VisualConfig } from '../../config/visualConfig';

/**
 * Render an outcome node (square with label).
 */
export function renderOutcomeNode(
  container: Container,
  nodeId: string,
  pos: NodePosition,
  config: VisualConfig,
  onHover?: (nodeId: string | null) => void
): void {
  const { node: nodeConfig, outcome: outcomeConfig, text: textConfig } = config;
  const graphics = new Graphics();

  // Draw square
  graphics
    .rect(
      pos.x - nodeConfig.outcomeSize,
      pos.y - nodeConfig.outcomeSize,
      nodeConfig.outcomeSize * 2,
      nodeConfig.outcomeSize * 2
    )
    .fill({ color: outcomeConfig.fillColor })
    .stroke({
      width: nodeConfig.strokeWidth,
      color: outcomeConfig.strokeColor,
      alpha: outcomeConfig.strokeAlpha,
    });

  // Make interactive
  graphics.eventMode = 'static';
  graphics.cursor = 'pointer';
  if (onHover) {
    graphics.on('pointerover', () => onHover(nodeId));
    graphics.on('pointerout', () => onHover(null));
  }

  container.addChild(graphics);

  // Outcome label
  if (pos.label) {
    const style = new TextStyle({
      fontFamily: textConfig.fontFamily,
      fontSize: textConfig.outcomeLabel.size,
      fill: textConfig.outcomeLabel.color,
    });
    const text = new Text({ text: pos.label, style });
    text.anchor.set(0.5, 0);
    text.x = pos.x;
    text.y = pos.y + nodeConfig.outcomeSize + 4;
    container.addChild(text);
  }
}
