import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        keywords: resolve(__dirname, 'keywords.html'),
        demo: resolve(__dirname, 'demo-manager.html')
      }
    }
  },
  publicDir: 'public'
})
