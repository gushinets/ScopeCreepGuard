import { configDefaults, defineConfig } from 'vitest/config'
import path from 'node:path'

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname),
    },
  },
  test: {
    exclude: [...configDefaults.exclude, 'scripts/docker-entrypoint.test.mjs'],
  },
})
