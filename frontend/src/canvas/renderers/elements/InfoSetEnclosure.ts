import { Container, Graphics, Text, TextStyle } from 'pixi.js';
import type { NodePosition } from '../../layout/treeLayout';
import type { VisualConfig } from '../../config/visualConfig';
import { getInfoSetColor } from '../../config/visualConfig';

/**
 * Render an information set enclosure (dashed rounded rect around nodes).
 */
export function renderInfoSetEnclosure(
  container: Container,
  infoSetId: string,
  nodes: NodePosition[],
  allInfoSets: string[],
  config: VisualConfig
): void {
  if (nodes.length < 2) return;

  const color = getInfoSetColor(infoSetId, allInfoSets);
  const graphics = new Graphics();
  const { node: nodeConfig, layout: layoutConfig, infoSet: infoSetConfig, text: textConfig } = config;

  // Calculate bounding box
  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;

  for (const node of nodes) {
    minX = Math.min(minX, node.x - nodeConfig.decisionRadius);
    maxX = Math.max(maxX, node.x + nodeConfig.decisionRadius);
    minY = Math.min(minY, node.y - nodeConfig.decisionRadius);
    maxY = Math.max(maxY, node.y + nodeConfig.decisionRadius);
  }

  // Add padding
  minX -= layoutConfig.infoSetPadding;
  maxX += layoutConfig.infoSetPadding;
  minY -= layoutConfig.infoSetPadding;
  maxY += layoutConfig.infoSetPadding;

  const width = maxX - minX;
  const height = maxY - minY;

  // Draw the dashed border
  drawDashedRoundedRect(
    graphics, minX, minY, width, height,
    infoSetConfig.cornerRadius, infoSetConfig.dashLength, infoSetConfig.gapLength,
    color, infoSetConfig.strokeWidth, infoSetConfig.strokeAlpha
  );

  // Add semi-transparent fill
  graphics
    .roundRect(minX, minY, width, height, infoSetConfig.cornerRadius)
    .fill({ color, alpha: infoSetConfig.fillAlpha });

  container.addChild(graphics);

  // Add label for the info set
  const labelStyle = new TextStyle({
    fontFamily: textConfig.fontFamily,
    fontSize: textConfig.infoSetLabel.size,
    fill: color,
    fontStyle: 'italic',
  });
  const label = new Text({ text: infoSetId, style: labelStyle });
  label.anchor.set(0.5, 1);
  label.x = (minX + maxX) / 2;
  label.y = minY - 2;
  label.alpha = infoSetConfig.labelAlpha;
  container.addChild(label);
}

/**
 * Draw a dashed rounded rectangle.
 */
function drawDashedRoundedRect(
  graphics: Graphics,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
  dashLen: number,
  gapLen: number,
  color: number,
  strokeWidth: number,
  strokeAlpha: number
): void {
  // Helper to draw a dashed line segment
  const drawDashedLine = (x1: number, y1: number, x2: number, y2: number) => {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const length = Math.sqrt(dx * dx + dy * dy);
    const unitX = dx / length;
    const unitY = dy / length;

    let pos = 0;
    let drawing = true;
    while (pos < length) {
      const segmentEnd = Math.min(pos + (drawing ? dashLen : gapLen), length);
      if (drawing) {
        graphics
          .moveTo(x1 + unitX * pos, y1 + unitY * pos)
          .lineTo(x1 + unitX * segmentEnd, y1 + unitY * segmentEnd)
          .stroke({ width: strokeWidth, color, alpha: strokeAlpha });
      }
      pos = segmentEnd;
      drawing = !drawing;
    }
  };

  // Top edge (excluding corners)
  drawDashedLine(x + radius, y, x + width - radius, y);
  // Right edge
  drawDashedLine(x + width, y + radius, x + width, y + height - radius);
  // Bottom edge
  drawDashedLine(x + width - radius, y + height, x + radius, y + height);
  // Left edge
  drawDashedLine(x, y + height - radius, x, y + radius);

  // Draw corner arcs (as small dashed segments approximating arcs)
  const drawDashedArc = (cx: number, cy: number, startAngle: number, endAngle: number) => {
    const steps = 8;
    const angleStep = (endAngle - startAngle) / steps;
    let drawing = true;
    for (let i = 0; i < steps; i += 2) {
      const a1 = startAngle + angleStep * i;
      const a2 = startAngle + angleStep * (i + 1);
      if (drawing) {
        graphics
          .moveTo(cx + radius * Math.cos(a1), cy + radius * Math.sin(a1))
          .lineTo(cx + radius * Math.cos(a2), cy + radius * Math.sin(a2))
          .stroke({ width: strokeWidth, color, alpha: strokeAlpha });
      }
      drawing = !drawing;
    }
  };

  // Top-left corner
  drawDashedArc(x + radius, y + radius, Math.PI, Math.PI * 1.5);
  // Top-right corner
  drawDashedArc(x + width - radius, y + radius, Math.PI * 1.5, Math.PI * 2);
  // Bottom-right corner
  drawDashedArc(x + width - radius, y + height - radius, 0, Math.PI * 0.5);
  // Bottom-left corner
  drawDashedArc(x + radius, y + height - radius, Math.PI * 0.5, Math.PI);
}
