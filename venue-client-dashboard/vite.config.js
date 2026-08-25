import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ command }) => ({
  plugins: [react()],
  server: { port: 5175 },
  base: command === 'build' ? (process.env.VITE_BASE || './') : '/',
}))
