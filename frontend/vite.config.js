import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',  // Listen on all network interfaces (required for devcontainer)
    port: 3000,
    strictPort: true,
    watch: {
      usePolling: true  // Required for file watching in some container environments
    },
    proxy: {
      '/api': {
        target: process.env.services__api__https__0 ||  process.env.services__api__http__0 || 'http://localhost:8091',
        changeOrigin: true,
      },
      '/ws': {
        target: process.env.services__api__https__0 ||  process.env.services__api__http__0 || 'http://localhost:8091',
        changeOrigin: true,
        ws: true
      }
    }
  }
})
