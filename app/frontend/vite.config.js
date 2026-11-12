import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Saat `npm run dev`, permintaan /api diteruskan ke backend Go di laptop (port 8080 bawaan, atau VITE_PROXY_TARGET dari .env).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react()],
    test: {
      environment: 'jsdom',
      include: ['src/__tests__/**/*.test.{js,jsx}'],
    },
    server: {
      port: 5173,
      proxy: {
        '/api': env.VITE_PROXY_TARGET || process.env.VITE_PROXY_TARGET || 'http://localhost:8080',
      },
    },
  }
})
