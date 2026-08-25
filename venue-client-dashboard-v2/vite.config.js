// Venue client dashboard dev server on 5176 (admin uses 5173, bCloud client 5174).
// Production build base is relative by default —
// VITE_BASE can override it at deploy time, local dev stays "/".
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ command }) => ({
  base: command === 'build' ? (process.env.VITE_BASE || './') : '/',
  plugins: [react()],
  server: {
    port: 5176,
    // dev-only: forward API calls to the live server (no CORS needed)
    proxy: { '/client-api': { target: 'https://portal.venuemarketplace.xyz', changeOrigin: true } },
  },
}))
