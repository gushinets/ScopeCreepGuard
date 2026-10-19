import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.SCOPE_GUARD_API_ORIGIN || 'http://127.0.0.1:8000'
  const parsed = new URL(target)
  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.origin !== target || parsed.username || parsed.password) throw new Error('Invalid API upstream origin')
  return {
    plugins: [react()],
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    server: { proxy: { '/api': { target, changeOrigin: false, timeout: 0, proxyTimeout: 0,
      configure(proxy) {
        proxy.on('error', (_error, _request, response) => {
          if ('writeHead' in response && !response.headersSent) response.writeHead(503, { 'Content-Type': 'application/json', 'Cache-Control': 'private, no-store' }).end('{"error":"errors.requestFailed"}')
        })
      },
    } } },
    preview: { proxy: { '/api': { target, changeOrigin: false, timeout: 0, proxyTimeout: 0 } } },
  }
})
