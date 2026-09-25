import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'

export default defineConfig({
  plugins: [
    react(),
    // `npm run analyze`: a treemap of what each chunk is made of, with gzip and
    // brotli sizes. Written beside package.json, never into dashboard-dist,
    // which the dashboard serves live.
    ...(process.env.ANALYZE
      ? [visualizer({ filename: 'paket-analizi.html', template: 'treemap', gzipSize: true, brotliSize: true })]
      : []),
  ],
  build: {
    outDir: '../dashboard-dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        // Carbon and React change far less often than app code; giving them
        // their own chunks keeps them cached across dashboard deploys and
        // brings each chunk under the size warning threshold.
        manualChunks(id: string) {
          if (!id.includes('node_modules')) return
          if (id.includes('@carbon')) return 'carbon'
          if (id.includes('react-router')) return 'router'
          if (/[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/.test(id)) return 'react'
        }
      }
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8085'
    }
  }
})
