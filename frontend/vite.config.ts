import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import { fileURLToPath, URL } from 'node:url'

// VITE_API_TARGET points the dev proxy at a backend other than a local one.
// Set it in the shell or in frontend/.env.local, e.g.
// VITE_API_TARGET=https://logs.offlinesoftware.solutions
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', 'VITE_')
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:8000'

  return {
    plugins: [
      vue(),
      vuetify({ autoImport: true }),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            echarts: ['echarts', 'vue-echarts'],
          },
        },
      },
    },
    server: {
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        }
      }
    }
  }
})
