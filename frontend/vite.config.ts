import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = process.env.API_PROXY_TARGET || env.API_PROXY_TARGET || 'http://localhost:8001'
  return {
    plugins: [react()],
    build: {
      rollupOptions: { output: { manualChunks: { charts: ['recharts'] } } },
    },
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': { target, changeOrigin: true },
        '/docs': { target, changeOrigin: true },
        '/openapi.json': { target, changeOrigin: true },
      },
    },
  }
})
