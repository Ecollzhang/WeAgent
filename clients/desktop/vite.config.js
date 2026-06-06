import { defineConfig } from 'vite'
import path from 'path'
import vue from '@vitejs/plugin-vue2'

export default defineConfig({
  plugins: [vue()],
  base: './',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
})
