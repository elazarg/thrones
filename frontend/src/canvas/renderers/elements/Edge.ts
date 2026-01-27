import { Container, Graphics, TextStyle } from 'pixi.js';
import { createText } from '../../utils/textUtils';
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

  // Draw action label - positioned just above the target node
  // This keeps it separate from probability labels which appear at midpoint
  const labelX = edge.toX;
  const labelY = edge.toY - nodeConfig.decisionRadius - 8; // Just above target node

  const labelStyle = new TextStyle({
    fontFamily: textConfig.fontFamily,
    fontSize: textConfig.actionLabel.size,
    fill: isDominated ? textConfig.actionLabel.dominatedColor : textConfig.actionLabel.color,
    fontStyle: isDominated ? 'italic' : 'normal',
  });

  const label = createText({ text: edge.label, style: labelStyle });
  label.anchor.set(0.5, 1); // Anchor at bottom center
  label.x = labelX;
  label.y = labelY;
  label.alpha = alpha;
  container.addChild(label);

  // Draw warning icon if present - next to action label
  if (edge.warning) {
    const warningStyle = new TextStyle({
      fontFamily: textConfig.fontFamily,
      fontSize: config.warning.iconSize,
      fill: config.warning.color,
    });
    const warning = createText({ text: '\u26A0', style: warningStyle });
    warning.anchor.set(0.5, 1);
    warning.x = labelX + label.width / 2 + 8;
    warning.y = labelY;
    warning.alpha = config.warning.iconAlpha;
    container.addChild(warning);
  }
}
