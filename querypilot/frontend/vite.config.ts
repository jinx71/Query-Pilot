import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// During development, proxy API calls to the FastAPI backend so the frontend
// can call same-origin '/api/...' paths without CORS friction.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
});
