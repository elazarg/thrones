import { Text, TextStyle } from 'pixi.js';
import type { TextStyleOptions } from 'pixi.js';

const MAX_TEXT_RESOLUTION = 8;

// Module-level text resolution — updated by viewport zoom handler
const dpr = window.devicePixelRatio || 1;
let _textResolution = Math.max(2, dpr);

export function getTextResolution(): number {
  return _textResolution;
}

export function setTextResolution(resolution: number): void {
  _textResolution = resolution;
}

/**
 * Compute the ideal text resolution for a given viewport zoom scale.
 * Rule: clamp(dpr * scale, base=max(2, dpr), max=MAX_TEXT_RESOLUTION)
 */
export function computeTextResolution(scale: number): number {
  const base = Math.max(2, dpr);
  return Math.min(MAX_TEXT_RESOLUTION, Math.max(base, Math.ceil(dpr * scale)));
}

/** Options accepted by createText — matches the CanvasTextOptions constructor overload. */
interface CreateTextOptions {
  text?: string | number | { toString(): string };
  style?: TextStyle | TextStyleOptions;
  [key: string]: unknown;
}

/**
 * Create a Text object with the current shared text resolution.
 * Drop-in replacement for `new Text({...})`.
 */
export function createText(options: CreateTextOptions): Text {
  const text = new Text(options);
  text.resolution = _textResolution;
  return text;
}
