import { config } from 'dotenv'
import { defineConfig } from 'drizzle-kit'

config({ path: '.env.local' })
config()

if (!process.env.DATABASE_URL) {
  console.error(
    JSON.stringify({
      event: 'config_missing',
      variable: 'DATABASE_URL',
      source: 'drizzle.config.ts',
    }),
  )
  throw new Error('DATABASE_URL is required')
}

export default defineConfig({
  schema: './lib/db/schema.ts',
  out: './drizzle',
  dialect: 'postgresql',
  dbCredentials: {
    url: process.env.DATABASE_URL,
  },
})
