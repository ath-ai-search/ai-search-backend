// Vite config — runs the React dev server on port 5177
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The production build uses RELATIVE asset paths ('./') by default so the
// bundle works no matter what path the server mounts the dashboard on.
// A server can still override that at build time with VITE_BASE:
//   production build : VITE_BASE=<mount path>  (optional, set by the server)
//   local dev        : "/" (unchanged — npm run dev still opens at /)
export default defineConfig(({ command }) => ({
  base: command === 'build' ? (process.env.VITE_BASE || './') : '/',
  plugins: [react()],
  server: { port: 5177 },
}))
