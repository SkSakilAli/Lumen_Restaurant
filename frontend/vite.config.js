// Copyright (c) 2026 Lumen Solutions
// SPDX-License-Identifier: AGPL-3.0-only
// "LumenPOS" is a trademark of Lumen Solutions. See TRADEMARKS.md.
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Build straight into the Frappe app's public folder with fixed filenames so
// lumen_restaurants/www/pos.html can reference /assets/lumen_restaurants/pos/pos.js and pos.css.
export default defineConfig({
  plugins: [vue()],
  base: '/assets/lumen_restaurants/pos/',
  build: {
    outDir: '../lumen_restaurants/public/pos',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: 'pos.js',
        // A language file (locales/<code>.js) is its own chunk. The hash gives
        // it a new name whenever its text changes, so neither the browser's
        // cache of /assets nor the service worker keeps an old translation.
        chunkFileNames: 'chunk-[name]-[hash].js',
        assetFileNames: (assetInfo) =>
          assetInfo.name && assetInfo.name.endsWith('.css') ? 'pos.css' : 'asset-[name][extname]',
      },
    },
  },
  server: {
    port: 8080,
    proxy: {
      '^/(api|assets|files)': {
        target: 'http://localhost:8000', // local bench during development
        changeOrigin: true,
      },
    },
  },
})
