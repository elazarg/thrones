import { Container, Graphics, Text, TextStyle } from 'pixi.js';
import type { EdgePosition } from '../../layout/treeLayout';
import type { VisualConfig } from '../../config/visualConfig';

/**
 * Render an edge (connection between nodes).
 */
export function renderEdge(
  container: Container,
  edge: EdgePosition,
  config: VisualConfig,
  options?: { dominated?: boolean }
): void {
  const graphics = new Graphics();
  const { node: nodeConfig, edge: edgeConfig, text: textConfig } = config;

  const isDominated = options?.dominated ?? !!edge.warning;
  const alpha = isDominated ? edgeConfig.dominatedAlpha : 1;

  // Draw the edge line
  graphics
    .moveTo(edge.fromX, edge.fromY + nodeConfig.decisionRadius)
    .lineTo(edge.toX, edge.toY - nodeConfig.decisionRadius)
    .stroke({ width: edgeConfig.width, color: edgeConfig.color, alpha });

  container.addChild(graphics);

  // Draw action label
  const midX = (edge.fromX + edge.toX) / 2;
  const midY = (edge.fromY + edge.toY) / 2;

  const labelStyle = new TextStyle({
    fontFamily: textConfig.fontFamily,
    fontSize: textConfig.actionLabel.size,
    fill: isDominated ? textConfig.actionLabel.dominatedColor : textConfig.actionLabel.color,
    fontStyle: isDominated ? 'italic' : 'normal',
  });

  const label = new Text({ text: edge.label, style: labelStyle });
  label.anchor.set(0.5, 0.5);
  label.x = midX + edgeConfig.labelOffset;
  label.y = midY;
  label.alpha = alpha;
  container.addChild(label);

  // Draw warning icon if present
  if (edge.warning) {
    const warningStyle = new TextStyle({
      fontFamily: textConfig.fontFamily,
      fontSize: config.warning.iconSize,
      fill: config.warning.color,
    });
    const warning = new Text({ text: '\u26A0', style: warningStyle });
    warning.anchor.set(0.5, 0.5);
    warning.x = midX + edgeConfig.labelOffset;
    warning.y = midY + 14;
    warning.alpha = config.warning.iconAlpha;
    container.addChild(warning);
  }
}
