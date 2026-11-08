import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiProxy = { '/api': 'http://127.0.0.1:8765' };

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true, proxy: apiProxy },
  preview: { port: 4173, strictPort: true, proxy: apiProxy },
  build: { chunkSizeWarningLimit: 900 },
});
