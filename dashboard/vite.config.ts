import { fileURLToPath } from 'node:url'
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
      // İki giriş: uygulama ve baskı görünümü (plan 2026-10-25 Görev 1). Baskı uygulama kabuğunu yüklemez.
      input: {
        main: fileURLToPath(new URL('./index.html', import.meta.url)),
        baski: fileURLToPath(new URL('./baski.html', import.meta.url)),
      },
      output: {
        // Carbon and React change far less often than app code; giving them
        // their own chunks keeps them cached across dashboard deploys and
        // brings each chunk under the size warning threshold.
        manualChunks(id: string) {
          if (!id.includes('node_modules')) return
          // Carbon AI Chat ve bağımlılıkları (web components, lit, markdown-it, tiptap, CodeMirror)
          // yalnız asistan açıldığında yüklenir: tembel import'un kendi parçasında kalırlar.
          if (/[\\/]node_modules[\\/](@carbon[\\/](ai-chat|ai-chat-components|web-components)|lit|@lit|lit-html|lit-element|@tiptap|prosemirror-[^\\/]+|@codemirror|@lezer|markdown-it|dompurify)[\\/]/.test(id)) return
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
