import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { port: 3000, host: '127.0.0.1' },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        // Forma de funcao: aceita tanto pelo Rollup (vite <=7) quanto pelo
        // Rolldown (vite 8+). A forma de objeto e rejeitada pelo Rolldown com
        // "manualChunks is not a function".
        manualChunks(id: string) {
          if (id.includes('lightweight-charts')) return 'charts';
          if (id.includes('@tauri-apps/api') || id.includes('@tauri-apps/plugin-notification')) {
            return 'tauri';
          }
          return undefined;
        },
      },
    },
  },
});

