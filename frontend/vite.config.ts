import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
    // PixiJS is ~550KB minified - reasonable for a 2D graphics engine
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          // Split large vendor libraries into separate cached chunks
          'pixi': ['pixi.js', 'pixi-viewport'],
          'charts': ['recharts'],
        },
      },
    },
  },
});
