/**
 * Shared utility functions for overlays.
 */
import { Container } from 'pixi.js';

/**
 * Clear an overlay container by its label.
 * Finds the container with the given label, removes it from parent,
 * and destroys it along with all children.
 *
 * @param container - The parent container to search in
 * @param label - The unique label of the overlay container to clear
 */
export function clearOverlayByLabel(container: Container, label: string): void {
  const overlayContainer = container.children.find((child) => child.label === label);
  if (overlayContainer) {
    container.removeChild(overlayContainer);
    overlayContainer.destroy({ children: true });
  }
}
