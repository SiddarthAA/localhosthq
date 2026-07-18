import { defineConfig } from 'vite'
import { fileURLToPath, URL } from 'node:url'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: true, // bind all interfaces (incl. the tailnet), not just loopback
    port: 5177,
    // let Vite 8 accept the tailnet hostname + the .ts.net domain
    allowedHosts: ['shawarma', '.chipmunk-balance.ts.net'],
  },
})
