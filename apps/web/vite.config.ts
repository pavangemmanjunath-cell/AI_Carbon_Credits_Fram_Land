import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// The repository root holds the single `.env` (see /.env.example); Vite reads
// the VITE_* variables from there so API and web share one file.
const repoRoot = fileURLToPath(new URL('../..', import.meta.url));

export default defineConfig({
  plugins: [react(), tailwindcss()],
  envDir: repoRoot,
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: { port: 5173, strictPort: false, host: true },
  preview: { port: 4173 },
  build: {
    target: 'es2022',
    sourcemap: false,
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        // The map stack (MapLibre), charts and drawing tools live in their own
        // chunks so the landing page and the app shell stay small. React gets a
        // vendor chunk of its own: otherwise Rollup folds it into the first
        // manual chunk that depends on it (charts) and every page preloads charts.
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (/node_modules\/(react|react-dom|scheduler|use-sync-external-store)\//.test(id))
              return 'react';
            if (id.includes('maplibre-gl')) return 'maplibre';
            if (id.includes('recharts') || id.includes('d3-') || id.includes('victory-vendor'))
              return 'charts';
            if (id.includes('terra-draw')) return 'draw';
            if (id.includes('@turf')) return 'turf';
          }
          return undefined;
        },
      },
    },
  },
});
