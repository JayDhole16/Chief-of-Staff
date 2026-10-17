import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const configDir = path.dirname(fileURLToPath(import.meta.url))

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(configDir, './src'),
        '@/mocks': path.resolve(configDir, './src/mocks'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  }
})
