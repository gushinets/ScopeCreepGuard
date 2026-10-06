import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import postgres from 'postgres'
import { drizzle } from 'drizzle-orm/postgres-js'
import { migrate } from 'drizzle-orm/postgres-js/migrator'
import * as schema from '@/lib/db/schema'
import { analysisFixture, documentFixture } from './fixtures'

const session = vi.hoisted(() => ({ userId: '10000000-0000-4000-8000-000000000001' as string | null }))
vi.mock('@/lib/auth/current-user', () => ({ getCurrentUser: async () => session.userId ? { id: session.userId } : null }))
vi.mock('next-intl/server', () => ({ getLocale: async () => 'en' }))
vi.mock('@/lib/llm/openai', () => ({ analyzeWithOpenAI: async () => analysisFixture, analyzeFailureResponse: () => ({ error: 'errors.analysisFailed', status: 500 }) }))
vi.mock('@/lib/llm/rate-limit', () => ({ allowAnalyze: () => true }))

const owner = '10000000-0000-4000-8000-000000000001'
const other = '10000000-0000-4000-8000-000000000002'
const projectId = '10000000-0000-4000-8000-000000000003'
const token = '10000000-0000-4000-8000-000000000004'
const body = { projectId, request: 'Add another page', locale: 'en', idempotencyKey: token, analysisSnapshot: analysisFixture, draftDocument: documentFixture }
const request = (method: string, data?: unknown) => new Request('http://localhost/api/drafts', { method, ...(data ? { body: JSON.stringify(data) } : {}) })
let sql: ReturnType<typeof postgres>
let collection: typeof import('@/app/api/drafts/route')
let detail: typeof import('@/app/api/drafts/[id]/route')
let analyze: typeof import('@/app/api/analyze/route')
let projectsData: typeof import('@/lib/projects/data')
const context = (id: string) => ({ params: Promise.resolve({ id }) })

describe.skipIf(!process.env.TEST_DATABASE_URL)('PostgreSQL draft persistence', () => {
  beforeAll(async () => {
    sql = postgres(process.env.TEST_DATABASE_URL!, { max: 5, onnotice: () => {} })
    const db = drizzle(sql, { schema })
    await migrate(db, { migrationsFolder: 'drizzle' })
    vi.doMock('@/lib/db', () => ({ db }))
    collection = await import('@/app/api/drafts/route')
    detail = await import('@/app/api/drafts/[id]/route')
    analyze = await import('@/app/api/analyze/route')
    projectsData = await import('@/lib/projects/data')
  })
  beforeEach(async () => {
    session.userId = owner
    await sql`TRUNCATE users CASCADE`
    await sql`INSERT INTO users(id,email,password_hash) VALUES (${owner}, 'owner@example.test', 'unused'), (${other}, 'other@example.test', 'unused')`
    await sql`INSERT INTO projects(id,user_id,name,industry,scope,start_date,pricing_model,currency,hourly_rate) VALUES (${projectId}, ${owner}, 'Website', 'Development', 'Build exactly five pages. Further pages are outside the agreed scope.', '2026-01-01', 'hourly', 'EUR', 100)`
  })
  afterAll(async () => { await sql?.end(); vi.doUnmock('@/lib/db') })

  async function create() {
    const response = await collection.POST(request('POST', body))
    expect(response.status).toBe(201)
    return response.json()
  }

  it('analysis alone leaves history, drafts and lastChecked untouched', async () => {
    expect((await analyze.POST(request('POST', { projectId, request: body.request }))).status).toBe(200)
    expect(Number((await sql`SELECT count(*) AS n FROM history_entries`)[0].n)).toBe(0)
    expect(Number((await sql`SELECT count(*) AS n FROM drafts`)[0].n)).toBe(0)
    expect((await sql`SELECT last_checked FROM projects`)[0].last_checked).toBeNull()
  })
  it('creates one linked history and draft atomically and deduplicates concurrent retries', async () => {
    const responses = await Promise.all([collection.POST(request('POST', body)), collection.POST(request('POST', body))])
    const data = await Promise.all(responses.map((response) => response.json()))
    expect(data[0].draft.id).toBe(data[1].draft.id)
    expect(Number((await sql`SELECT count(*) AS n FROM history_entries`)[0].n)).toBe(1)
    expect(Number((await sql`SELECT count(*) AS n FROM drafts`)[0].n)).toBe(1)
    expect(data[0].draft.historyEntryId).toBe(data[0].entry.id)
    expect((await sql`SELECT last_checked::text AS date FROM projects`)[0].date).toBe(data[0].entry.date)
    expect((await projectsData.loadProjectForUser(projectId, owner))?.history[0].draftId).toBe(data[0].draft.id)
  })
  it('rolls back history and lastChecked if draft insertion fails', async () => {
    await sql`CREATE OR REPLACE FUNCTION fail_draft() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'injected failure'; END $$`
    await sql`CREATE TRIGGER fail_draft_insert BEFORE INSERT ON drafts FOR EACH ROW EXECUTE FUNCTION fail_draft()`
    try {
      expect((await collection.POST(request('POST', body))).status).toBe(500)
      expect(Number((await sql`SELECT count(*) AS n FROM history_entries`)[0].n)).toBe(0)
      expect(Number((await sql`SELECT count(*) AS n FROM drafts`)[0].n)).toBe(0)
      expect((await sql`SELECT last_checked FROM projects`)[0].last_checked).toBeNull()
    } finally {
      await sql`DROP TRIGGER fail_draft_insert ON drafts`
      await sql`DROP FUNCTION fail_draft()`
    }
  })
  it('GET restores every saved document and original analysis field', async () => {
    const created = await create()
    const response = await detail.GET(request('GET'), context(created.draft.id))
    expect(response.status).toBe(200)
    const restored = await response.json()
    expect(restored.draft.draftDocument).toEqual(documentFixture)
    expect(restored.draft.analysisSnapshot).toEqual(analysisFixture)
    expect(restored.draft.request).toBe('Add another page')
  })
  it('PUT replaces editable document but preserves original snapshot and history', async () => {
    const created = await create()
    const changed = { ...documentFixture, reply: { ...documentFixture.reply, text: 'Updated reply' }, changeOrder: { ...documentFixture.changeOrder!, additionalCost: '99', noAdditionalCharge: true } }
    const response = await detail.PUT(request('PUT', { draftDocument: changed }), context(created.draft.id))
    expect(response.status).toBe(200)
    const updated = (await response.json()).draft
    expect(updated.draftDocument).toEqual(changed)
    expect(updated.analysisSnapshot).toEqual(created.draft.analysisSnapshot)
    expect(updated.createdAt).toBe(created.draft.createdAt)
    expect(updated.historyEntryId).toBe(created.entry.id)
    expect(new Date(updated.updatedAt).getTime()).toBeGreaterThanOrEqual(new Date(created.draft.updatedAt).getTime())
    expect((await sql`SELECT summary FROM history_entries`)[0].summary).toBe('Extra page')
  })
  it('protects GET, PUT and lists from another authenticated user', async () => {
    const created = await create()
    session.userId = other
    expect((await detail.GET(request('GET'), context(created.draft.id))).status).toBe(404)
    expect((await detail.PUT(request('PUT', { draftDocument: documentFixture }), context(created.draft.id))).status).toBe(404)
    expect((await (await collection.GET()).json()).drafts).toEqual([])
    expect((await collection.POST(request('POST', body))).status).toBe(404)
    session.userId = owner
    const list = (await (await collection.GET()).json()).drafts
    expect(list).toHaveLength(1)
    expect(list[0]).toMatchObject({ id: created.draft.id, requestPreview: 'Add another page', projectName: 'Website', verdict: 'out_of_scope' })
    expect(list[0]).not.toHaveProperty('analysisSnapshot')
  })
  it('requires authentication and rejects malformed documents before insertion', async () => {
    session.userId = null
    expect((await collection.POST(request('POST', body))).status).toBe(401)
    expect((await collection.GET()).status).toBe(401)
    expect((await detail.GET(request('GET'), context(token))).status).toBe(401)
    expect((await detail.PUT(request('PUT', { draftDocument: documentFixture }), context(token))).status).toBe(401)
    session.userId = owner
    expect((await collection.POST(request('POST', { ...body, analysisSnapshot: {} }))).status).toBe(400)
    expect(Number((await sql`SELECT count(*) AS n FROM history_entries`)[0].n)).toBe(0)
  })
  it('loads legacy history without a draft and leaves evaluations compatible', async () => {
    await sql`INSERT INTO history_entries(project_id,date,request,verdict,summary) VALUES (${projectId}, '2026-10-01', 'Legacy request', 'in_scope', 'Included')`
    const project = await projectsData.loadProjectForUser(projectId, owner)
    expect(project?.history[0]).toMatchObject({ request: 'Legacy request', verdict: 'in_scope' })
    expect(project?.history[0].draftId).toBeUndefined()
  })
})
