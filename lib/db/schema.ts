import { sql } from 'drizzle-orm'
import {
  check,
  date,
  numeric,
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

export const pricingModelEnum = pgEnum('pricing_model', ['hourly', 'fixed'])
export const currencyEnum = pgEnum('currency', ['RUB', 'USD', 'EUR'])

export const evaluationAccuracyEnum = pgEnum('evaluation_accuracy', [
  'correct',
  'wrong',
  'debatable',
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
  startDate: date('start_date'),
  pricingModel: pricingModelEnum('pricing_model'),
  currency: currencyEnum('currency'),
  hourlyRate: numeric('hourly_rate', { precision: 14, scale: 2 }),
  fixedPrice: numeric('fixed_price', { precision: 14, scale: 2 }),
  lastChecked: date('last_checked'),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (table) => [
  check('projects_commercial_terms_consistent', sql`(
    (${table.startDate} IS NULL AND ${table.pricingModel} IS NULL AND ${table.currency} IS NULL AND ${table.hourlyRate} IS NULL AND ${table.fixedPrice} IS NULL)
    OR
    (${table.startDate} IS NOT NULL AND ${table.currency} IS NOT NULL AND (
      (${table.pricingModel} = 'hourly' AND ${table.hourlyRate} > 0 AND ${table.fixedPrice} IS NULL)
      OR (${table.pricingModel} = 'fixed' AND ${table.fixedPrice} > 0 AND ${table.hourlyRate} IS NULL)
    ))
  )`),
])

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

export const evaluationCases = pgTable(
  'evaluation_cases',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    userId: uuid('user_id')
      .notNull()
      .references(() => users.id, { onDelete: 'cascade' }),
    historyEntryId: uuid('history_entry_id')
      .unique()
      .references(() => historyEntries.id, { onDelete: 'set null' }),
    scope: text('scope').notNull(),
    request: text('request').notNull(),
    aiVerdict: verdictEnum('ai_verdict').notNull(),
    humanVerdict: verdictEnum('human_verdict'),
    aiReasoning: text('ai_reasoning').notNull(),
    accuracy: evaluationAccuracyEnum('accuracy').notNull(),
    industry: industryEnum('industry').notNull(),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    check(
      'evaluation_cases_accuracy_human_verdict',
      sql`(
        (${table.accuracy} = 'debatable' AND ${table.humanVerdict} IS NULL)
        OR
        (${table.accuracy} = 'correct' AND ${table.humanVerdict} IS NOT NULL AND ${table.humanVerdict} = ${table.aiVerdict})
        OR
        (${table.accuracy} = 'wrong' AND ${table.humanVerdict} IS NOT NULL AND ${table.humanVerdict} <> ${table.aiVerdict})
      )`,
    ),
  ],
)
