import { drizzle } from 'drizzle-orm/postgres-js'
import postgres from 'postgres'
import * as schema from './schema'

const databaseUrl = process.env.DATABASE_URL

if (!databaseUrl) {
  console.error(
    JSON.stringify({
      event: 'config_missing',
      variable: 'DATABASE_URL',
      source: 'lib/db/index.ts',
    }),
  )
  throw new Error('DATABASE_URL is required')
}

declare global {
  var scopeCreepGuardSql: postgres.Sql | undefined
}

const sql =
  globalThis.scopeCreepGuardSql ??
  postgres(databaseUrl, {
    max: 10,
  })

if (process.env.NODE_ENV !== 'production') {
  globalThis.scopeCreepGuardSql = sql
}

export const db = drizzle(sql, { schema })
