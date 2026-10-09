import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Relative base so the built app works from any folder or static host.
export default defineConfig({
  base: './',
  plugins: [react()],
  worker: { format: 'es' },
})
