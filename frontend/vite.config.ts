import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const backendUrl = process.env.VITE_BACKEND_URL || 'http://localhost:8000'
const backendWsUrl = backendUrl.replace('http', 'ws')

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/ws': {
        target: backendWsUrl,
        ws: true
      },
      '/games': {
        target: backendUrl
      }
    }
  }
})
