import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
<<<<<<< HEAD
  const configDir = path.dirname(fileURLToPath(import.meta.url))
=======
>>>>>>> 7fac91b5d6eca0b999cbddaba8c49e1d87bbe5ec

  return {
    plugins: [react()],
    resolve: {
      alias: {
<<<<<<< HEAD
        '@': path.resolve(configDir, './src'),
        '@/mocks': path.resolve(configDir, './src/mocks'),
=======
        '@': path.resolve(__dirname, './src'),
        '@/mocks': path.resolve(__dirname, './src/mocks'),
>>>>>>> 7fac91b5d6eca0b999cbddaba8c49e1d87bbe5ec
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
