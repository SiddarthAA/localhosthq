import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // bind all interfaces (incl. the tailnet), not just loopback
    port: 5177,
    // let Vite 8 accept the tailnet hostname + the .ts.net domain
    allowedHosts: ['shawarma', '.chipmunk-balance.ts.net'],
  },
})
