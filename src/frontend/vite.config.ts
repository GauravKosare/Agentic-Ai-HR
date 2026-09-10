import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// In dev, calls to /api/* are proxied to the FastAPI backend on :8000 so the
// browser sees them as same-origin (no CORS). In prod the frontend is deployed
// separately, so it uses VITE_API_BASE_URL instead — see src/api.ts.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
