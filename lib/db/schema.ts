import {
  date,
  pgEnum,
  pgTable,
  text,
  timestamp,
  uuid,
} from 'drizzle-orm/pg-core'

export const industryEnum = pgEnum('industry', [
  'Development',
  'Design',
  'Marketing',
])

export const verdictEnum = pgEnum('verdict', [
  'in_scope',
  'borderline',
  'out_of_scope',
])

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: text('email').notNull().unique(),
  passwordHash: text('password_hash').notNull(),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
})

export const projects = pgTable('projects', {
  id: uuid('id').primaryKey().defaultRandom(),
  userId: uuid('user_id')
    .notNull()
    .references(() => users.id, { onDelete: 'cascade' }),
  name: text('name').notNull(),
  client: text('client'),
  industry: industryEnum('industry').notNull(),
  scope: text('scope').notNull(),
  lastChecked: date('last_checked'),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
})

export const historyEntries = pgTable('history_entries', {
  id: uuid('id').primaryKey().defaultRandom(),
  projectId: uuid('project_id')
    .notNull()
    .references(() => projects.id, { onDelete: 'cascade' }),
  date: date('date').notNull(),
  request: text('request').notNull(),
  verdict: verdictEnum('verdict').notNull(),
  summary: text('summary').notNull(),
})
