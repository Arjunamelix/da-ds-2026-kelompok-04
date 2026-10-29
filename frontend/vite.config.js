import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Saat `npm run dev`, permintaan /api diteruskan ke backend Go di laptop (port 8080).
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    include: ['src/__tests__/**/*.test.{js,jsx}'],
  },
  server: {
    port: 5173,
    proxy: {
      '/api': process.env.VITE_PROXY_TARGET || 'http://localhost:8080',
    },
  },
})