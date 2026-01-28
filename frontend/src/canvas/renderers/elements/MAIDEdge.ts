import { Container, Graphics } from 'pixi.js';
import type { MAIDEdgePosition, MAIDNodePosition } from '../../layout/maidLayout';
import type { VisualConfig } from '../../config/visualConfig';

/**
 * Get the node radius based on node type.
 */
function getNodeRadius(nodeType: 'decision' | 'utility' | 'chance', config: VisualConfig): number {
  const { maid: maidConfig } = config;
  switch (nodeType) {
    case 'decision':
      return maidConfig.decisionRadius;
    case 'utility':
      return maidConfig.utilityDiamondSize;
    case 'chance':
      return maidConfig.chanceHexagonSize;
    default:
      return maidConfig.decisionRadius;
  }
}

/**
 * Render a MAID edge with arrowhead.
 */
export function renderMAIDEdge(
  container: Container,
  edge: MAIDEdgePosition,
  sourceNode: MAIDNodePosition,
  targetNode: MAIDNodePosition,
  config: VisualConfig
): void {
  const { maid: maidConfig } = config;
  const graphics = new Graphics();

  // Calculate edge start and end points (offset by node radius)
  const dx = edge.toX - edge.fromX;
  const dy = edge.toY - edge.fromY;
  const dist = Math.sqrt(dx * dx + dy * dy);

  if (dist === 0) return;

  const nx = dx / dist;
  const ny = dy / dist;

  const sourceRadius = getNodeRadius(sourceNode.type, config);
  const targetRadius = getNodeRadius(targetNode.type, config);

  const startX = edge.fromX + nx * sourceRadius;
  const startY = edge.fromY + ny * sourceRadius;
  const endX = edge.toX - nx * targetRadius;
  const endY = edge.toY - ny * targetRadius;

  // Check if edge spans multiple layers (need curve)
  const layerDiff = Math.abs(targetNode.layer - sourceNode.layer);
  const usesCurve = layerDiff > 1 || (layerDiff === 0 && dist > maidConfig.minNodeSpacing);

  if (usesCurve) {
    // Bezier curve for long edges
    const midX = (startX + endX) / 2;
    const midY = (startY + endY) / 2;

    // Control point offset perpendicular to the line
    const perpX = -ny * 30;
    const perpY = nx * 30;

    graphics
      .moveTo(startX, startY)
      .quadraticCurveTo(midX + perpX, midY + perpY, endX, endY)
      .stroke({ width: maidConfig.edgeWidth, color: maidConfig.edgeColor });
  } else {
    // Straight line for adjacent layers
    graphics
      .moveTo(startX, startY)
      .lineTo(endX, endY)
      .stroke({ width: maidConfig.edgeWidth, color: maidConfig.edgeColor });
  }

  // Draw arrowhead
  const arrowSize = maidConfig.arrowSize;
  const arrowAngle = Math.PI / 6; // 30 degrees

  const arrowX1 = endX - arrowSize * Math.cos(Math.atan2(ny, nx) - arrowAngle);
  const arrowY1 = endY - arrowSize * Math.sin(Math.atan2(ny, nx) - arrowAngle);
  const arrowX2 = endX - arrowSize * Math.cos(Math.atan2(ny, nx) + arrowAngle);
  const arrowY2 = endY - arrowSize * Math.sin(Math.atan2(ny, nx) + arrowAngle);

  graphics
    .moveTo(endX, endY)
    .lineTo(arrowX1, arrowY1)
    .moveTo(endX, endY)
    .lineTo(arrowX2, arrowY2)
    .stroke({ width: maidConfig.edgeWidth, color: maidConfig.edgeColor });

  container.addChild(graphics);
}
