import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/health': { target: 'http://localhost:5000', changeOrigin: true },
      '/dashboard-data': { target: 'http://localhost:5000', changeOrigin: true },
      '/predict': { target: 'http://localhost:5000', changeOrigin: true },
      '/predict/batch': { target: 'http://localhost:5000', changeOrigin: true },
      '/recommendations': { target: 'http://localhost:5000', changeOrigin: true },
      '/product-alternatives': { target: 'http://localhost:5000', changeOrigin: true },
      '/model/info': { target: 'http://localhost:5000', changeOrigin: true },
      '/catalog': { target: 'http://localhost:5000', changeOrigin: true },
      '/category-comparison': { target: 'http://localhost:5000', changeOrigin: true },
      '/steady-products': { target: 'http://localhost:5000', changeOrigin: true },
      '/inventory-actions': { target: 'http://localhost:5000', changeOrigin: true },
      '/monitoring': { target: 'http://localhost:5000', changeOrigin: true },
    },
    // SPA fallback for React Router
    middlewareMode: false,
    fs: { strict: false },
  },
  appType: 'spa',
})
