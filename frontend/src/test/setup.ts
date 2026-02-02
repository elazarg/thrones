import '@testing-library/jest-dom';

// Mock canvas for Pixi.js tests
HTMLCanvasElement.prototype.getContext = () => null;

// Mock ResizeObserver
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
