import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The frontend talks to a relative `/api` and Vite forwards it to FastAPI,
// stripping the prefix. That keeps the generated paths (`/studies/{study_id}`)
// exactly as they appear in openapi.json — no prefix baked into the contract.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
