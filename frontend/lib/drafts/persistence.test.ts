import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import postgres from 'postgres'
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, rmSync } from 'node:fs'
import { join, resolve, sep } from 'node:path'
import { tmpdir } from 'node:os'
import { drizzle } from 'drizzle-orm/postgres-js'
import { migrate } from 'drizzle-orm/postgres-js/migrator'
import * as schema from '@/lib/db/schema'
import { analysisFixture, documentFixture, projectSnapshotFixture } from './fixtures'

import { issueDraftProof } from '@/tests/draft-proof-fixture'
import { createSessionToken } from '@/tests/session-fixture'
import { pythonProof } from '@/tests/python-proof-fixture'

vi.mock('server-only', () => ({}))

const session = vi.hoisted(() => ({ userId: '10000000-0000-4000-8000-000000000001' as string | null }))
vi.mock('@/lib/auth/current-user', () => ({ getCurrentUser: async () => session.userId ? { id: session.userId } : null }))
vi.mock('next-intl/server', () => ({ getLocale: async () => 'en' }))

const owner = '10000000-0000-4000-8000-000000000001'
const other = '10000000-0000-4000-8000-000000000002'
const projectId = '10000000-0000-4000-8000-000000000003'
const token = '10000000-0000-4000-8000-000000000004'
const body = { proof: '', projectId, request: 'Add another page', locale: 'en', idempotencyKey: token, analysisSnapshot: analysisFixture, draftDocument: documentFixture }
const cookies = new Map<string, string>()
const request = (method: string, data?: unknown) => new Request('http://localhost/api/drafts', {
  method, headers: { cookie: session.userId ? cookies.get(session.userId) ?? '' : '' },
  ...(data ? { body: JSON.stringify(data) } : {}),
})
let sql: ReturnType<typeof postgres>
let collection: typeof import('@/app/api/drafts/route')
let detail: typeof import('@/app/api/drafts/[id]/route')
let analyze: typeof import('@/app/api/analyze/route')
let projectsData: typeof import('@/lib/projects/data')
let projectRoute: typeof import('@/app/api/projects/[id]/route')
const context = (id: string) => ({ params: Promise.resolve({ id }) })

describe.skipIf(!process.env.TEST_DATABASE_URL)('PostgreSQL draft persistence', () => {
  beforeAll(async () => {
    sql = postgres(process.env.TEST_DATABASE_URL!, { max: 5, onnotice: () => {} })
    const db = drizzle(sql, { schema })
    // Exercise the production migrator from ANY-548's journal through the new migration.
    const baselineDir = mkdtempSync(join(tmpdir(), 'scg-any547-migrations-'))
    try {
      mkdirSync(join(baselineDir, 'meta'))
      const journal = JSON.parse(readFileSync('drizzle/meta/_journal.json', 'utf8'))
      const baseline = { ...journal, entries: journal.entries.filter((entry: { idx: number }) => entry.idx <= 5) }
      writeFileSync(join(baselineDir, 'meta/_journal.json'), JSON.stringify(baseline))
      for (const entry of baseline.entries) writeFileSync(join(baselineDir, entry.tag + '.sql'), readFileSync('drizzle/' + entry.tag + '.sql'))
      await migrate(db, { migrationsFolder: baselineDir })
      const before = await sql`SELECT hash, created_at FROM drizzle.__drizzle_migrations ORDER BY id`
      await migrate(db, { migrationsFolder: 'drizzle' })
      const after = await sql`SELECT hash, created_at FROM drizzle.__drizzle_migrations ORDER BY id`
      expect(after.slice(0, 6)).toEqual(before.slice(0, 6))
      expect(after).toHaveLength(7)
      expect((await sql`SELECT confdeltype FROM pg_constraint WHERE conname = 'evaluation_cases_history_entry_id_history_entries_id_fk'`)[0].confdeltype).toBe('c')
      expect(await sql`SELECT column_name FROM information_schema.columns WHERE table_name = 'projects' AND column_name = 'end_date'`).toHaveLength(0)
    } finally {
      if (!resolve(baselineDir).startsWith(resolve(tmpdir()) + sep)) throw new Error('Unexpected migration temp path')
      rmSync(baselineDir, { recursive: true })
    }
    vi.doMock('@/lib/db', () => ({ db }))
    collection = await import('@/app/api/drafts/route')
    detail = await import('@/app/api/drafts/[id]/route')
    analyze = await import('@/app/api/analyze/route')
    projectsData = await import('@/lib/projects/data')
    projectRoute = await import('@/app/api/projects/[id]/route')
  })
  beforeEach(async () => {
    vi.stubEnv('AUTH_SECRET', 'integration-test-secret-at-least-32-characters')
    if (!process.env.SCG_LEGACY_API_ORIGIN) throw new Error('Owned Python project gateway required')
    vi.stubEnv('SCOPE_GUARD_API_ORIGIN', process.env.SCG_LEGACY_API_ORIGIN)
    for (const id of [owner, other]) cookies.set(id, 'scg_session=' + await createSessionToken({ id, email: 'unused@example.test' }) + '; locale=en')
    body.proof = await issueDraftProof({ userId: owner, projectId, request: body.request, locale: 'en', analysisSnapshot: analysisFixture, projectSnapshot: projectSnapshotFixture })
    session.userId = owner
    await sql`TRUNCATE users CASCADE`
    await sql`INSERT INTO users(id,email,password_hash) VALUES (${owner}, 'owner@example.test', 'unused'), (${other}, 'other@example.test', 'unused')`
    await sql`INSERT INTO projects(id,user_id,name,industry,scope,start_date,pricing_model,currency,hourly_rate) VALUES (${projectId}, ${owner}, 'Website', 'Development', 'Build exactly five pages. Further pages are outside the agreed scope.', '2026-01-01', 'hourly', 'EUR', 100)`
  })
  afterAll(async () => { await sql?.end(); vi.doUnmock('@/lib/db'); vi.unstubAllEnvs() })

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
    body.proof = pythonProof('issue', { userId: owner, projectId, request: body.request, locale: 'en', analysisSnapshot: analysisFixture, projectSnapshot: projectSnapshotFixture })
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
    const response = await detail.PUT(request('PUT', { draftDocument: changed, analysisSnapshot: { ...analysisFixture, verdict: 'in_scope' }, projectSnapshot: { ...projectSnapshotFixture, scope: 'Forged' } }), context(created.draft.id))
    expect(response.status).toBe(200)
    const updated = (await response.json()).draft
    expect(updated.draftDocument).toEqual(changed)
    expect(updated.analysisSnapshot).toEqual(created.draft.analysisSnapshot)
    expect(updated.projectSnapshot).toEqual(created.draft.projectSnapshot)
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
    expect((await collection.POST(request('POST', body))).status).toBe(400)
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
    expect((await collection.POST(request('POST', { ...body, draftDocument: {} }))).status).toBe(400)
    expect(Number((await sql`SELECT count(*) AS n FROM history_entries`)[0].n)).toBe(0)
  })
  it('rejects browser-only forged snapshots before writing history or drafts', async () => {
    const forged = { ...body, proof: undefined, analysisSnapshot: { ...analysisFixture, verdict: 'in_scope', reasoning: 'Forged' } }
    const response = await collection.POST(request('POST', forged))
    expect(response.status).toBe(400)
    expect(Number((await sql`SELECT count(*) AS n FROM history_entries`)[0].n)).toBe(0)
    expect(Number((await sql`SELECT count(*) AS n FROM drafts`)[0].n)).toBe(0)
  })
  it('stores the original project conditions alongside the analysis', async () => {
    const created = await create()
    expect(created.draft.projectSnapshot).toMatchObject({
      name: 'Website', industry: 'Development',
      scope: 'Build exactly five pages. Further pages are outside the agreed scope.',
      startDate: '2026-01-01', endDate: null, pricingModel: 'hourly', currency: 'EUR',
      hourlyRate: '100.00', fixedPrice: null,
    })
  })


  it('ignores a forged browser snapshot and preserves verified proof snapshots', async () => {
    const response = await collection.POST(request('POST', {
      ...body, analysisSnapshot: { ...analysisFixture, reasoning: 'Forged reasoning', replies: { warm: 'Forged', neutral: 'Forged', firm: 'Forged' }, changeOrder: { ...analysisFixture.changeOrder, additionalCost: '999' } },
      projectSnapshot: { ...projectSnapshotFixture, hourlyRate: '999' },
    }))
    expect(response.status).toBe(201)
    const saved = (await response.json()).draft
    expect(saved.analysisSnapshot).toEqual(analysisFixture)
    expect(saved.projectSnapshot).toEqual(projectSnapshotFixture)
  })
  it.each([
    { projectId: other }, { request: 'Different request' }, { locale: 'ru' },
    { proof: 'malformed' },
  ])('rejects proof binding violations without partial writes', async (override) => {
    expect((await collection.POST(request('POST', { ...body, ...override }))).status).toBe(400)
    expect(Number((await sql`SELECT count(*) AS n FROM drafts`)[0].n)).toBe(0)
    expect(Number((await sql`SELECT count(*) AS n FROM history_entries`)[0].n)).toBe(0)
  })
  it('rejects expired proofs without partial writes', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(Date.now() - 7200_000))
    const proof = await issueDraftProof({ userId: owner, projectId, request: body.request, locale: 'en', analysisSnapshot: analysisFixture, projectSnapshot: projectSnapshotFixture })
    vi.useRealTimers()
    expect((await collection.POST(request('POST', { ...body, proof }))).status).toBe(400)
    expect(Number((await sql`SELECT count(*) AS n FROM history_entries`)[0].n)).toBe(0)
    expect(Number((await sql`SELECT count(*) AS n FROM drafts`)[0].n)).toBe(0)
  })
  it('keeps the analysis-time project snapshot when project changes before and after creation', async () => {
    const response = await analyze.POST(request('POST', { projectId, request: body.request, endDate: '2026-12-01', documentLanguage: 'en' }))
    const analysis = await response.json()
    expect(analysis.proof).toEqual(expect.any(String))
    await sql`UPDATE projects SET name = 'Renamed', scope = 'Changed scope', hourly_rate = 999 WHERE id = ${projectId}`
    const response2 = await collection.POST(request('POST', { ...body, proof: analysis.proof, draftDocument: { ...documentFixture, result: analysis.result } }))
    expect(response2.status).toBe(201)
    const created = (await response2.json()).draft
    expect(created.projectSnapshot).toEqual({ ...projectSnapshotFixture, clientName: null, endDate: '2026-12-01', documentLanguage: 'en' })
    await sql`UPDATE projects SET name = 'Changed again', hourly_rate = 333 WHERE id = ${projectId}`
    const reopened = (await (await detail.GET(request('GET'), context(created.id))).json()).draft
    expect(reopened.projectSnapshot).toEqual(created.projectSnapshot)
    expect((await (await collection.GET()).json()).drafts[0].projectName).toBe('Website')
  })
  it('keeps legacy persisted drafts readable and editable without fabricating a snapshot', async () => {
    const created = await create()
    await sql`UPDATE drafts SET project_snapshot = NULL WHERE id = ${created.draft.id}`
    const reopened = (await (await detail.GET(request('GET'), context(created.draft.id))).json()).draft
    expect(reopened.projectSnapshot).toBeNull()
    expect(reopened.draftDocument).toEqual(documentFixture)
    const response = await detail.PUT(request('PUT', { draftDocument: documentFixture }), context(created.draft.id))
    expect(response.status).toBe(200)
    expect((await response.json()).draft.projectSnapshot).toBeNull()
  })

  it('loads legacy history without a draft and leaves evaluations compatible', async () => {
    await sql`INSERT INTO history_entries(project_id,date,request,verdict,summary) VALUES (${projectId}, '2026-10-01', 'Legacy request', 'in_scope', 'Included')`
    const project = await projectsData.loadProjectForUser(projectId, owner)
    expect(project?.history[0]).toMatchObject({ request: 'Legacy request', verdict: 'in_scope' })
    expect(project?.history[0].draftId).toBeUndefined()
  })
  const projectInput = { name: 'Renamed', clientName: 'Current client', industry: 'Marketing', scope: 'Updated agreed scope with complete new commercial terms.', startDate: '2026-10-07', pricingModel: 'fixed', currency: 'USD', hourlyRate: '', fixedPrice: '5000' }
  it.each([null, other])('rejects project mutations by unauthenticated or non-owner users: %s', async userId => {
    const created = await create()
    session.userId = userId
    const status = userId === null ? 401 : 404
    expect((await projectRoute.PATCH(request('PATCH', projectInput), context(projectId))).status).toBe(status)
    expect((await projectRoute.DELETE(request('DELETE'), context(projectId))).status).toBe(status)
    session.userId = owner
    expect((await detail.GET(request('GET'), context(created.draft.id))).status).toBe(200)
    expect((await sql`SELECT name FROM projects WHERE id = ${projectId}`)[0].name).toBe('Website')
  })
  it('persists every project field without changing saved drafts, snapshots, history or evaluations', async () => {
    const created = await create()
    await sql`INSERT INTO evaluation_cases (user_id,history_entry_id,scope,request,ai_verdict,ai_reasoning,accuracy,industry) VALUES (${owner},${created.entry.id},'Original scope','Extra','out_of_scope','Original reasoning','debatable','Development')`
    const draftsBefore = await sql`SELECT * FROM drafts`
    const historyBefore = await sql`SELECT * FROM history_entries`
    const evaluationsBefore = await sql`SELECT * FROM evaluation_cases`
    const response = await projectRoute.PATCH(request('PATCH', { ...projectInput, endDate: '2099-01-01' }), context(projectId))
    expect(response.status).toBe(200)
    const updated = (await response.json()).project
    expect(updated).toMatchObject({ ...projectInput, fixedPrice: '5000.00', hourlyRate: null })
    expect(updated).not.toHaveProperty('endDate')
    expect(updated.history[0].draftId).toBe(created.draft.id)
    expect(await sql`SELECT * FROM drafts`).toEqual(draftsBefore)
    expect(await sql`SELECT * FROM history_entries`).toEqual(historyBefore)
    expect(await sql`SELECT * FROM evaluation_cases`).toEqual(evaluationsBefore)
    expect((await (await detail.GET(request('GET'), context(created.draft.id))).json()).draft).toEqual(created.draft)
  })
  it('captures persisted client name in signed snapshots and ignores browser-forged snapshots', async () => {
    await projectRoute.PATCH(request('PATCH', projectInput), context(projectId))
    const analyzed = await (await analyze.POST(request('POST', { projectId, request: body.request, endDate: '2026-12-01' }))).json()
    expect(analyzed.projectSnapshot.clientName).toBe('Current client')
    const document = { ...documentFixture, result: analyzed.result, projectDetails: { ...documentFixture.projectDetails, clientName: 'Current client' }, changeOrder: { ...documentFixture.changeOrder!, clientName: 'Current client' } }
    const saved = await (await collection.POST(request('POST', { ...body, proof: analyzed.proof, draftDocument: document, projectSnapshot: { clientName: 'Forged' } }))).json()
    expect(saved.draft.projectSnapshot.clientName).toBe('Current client')
    expect(saved.draft.draftDocument.changeOrder.clientName).toBe('Current client')
  })
  it('cascades project deletion through persisted drafts, history and evaluations while preserving other projects', async () => {
    const created = await create()
    const secondProject = '10000000-0000-4000-8000-000000000005'
    await sql`INSERT INTO projects(id,user_id,name,industry,scope) VALUES (${secondProject},${other},'Other project','Design','Scope')`
    const [secondHistory] = await sql`INSERT INTO history_entries(project_id,date,request,verdict,summary) VALUES (${secondProject},'2026-10-07','Extra','out_of_scope','Extra') RETURNING id`
    await sql`INSERT INTO drafts(project_id,history_entry_id,idempotency_key,analysis_snapshot,draft_document,locale,client_material_language) VALUES (${secondProject},${secondHistory.id},${token},${JSON.stringify(analysisFixture)}::jsonb,${JSON.stringify(documentFixture)}::jsonb,'en','en')`
    for (const [userId, historyId] of [[owner, created.entry.id], [other, secondHistory.id], [owner, null]]) {
      await sql`INSERT INTO evaluation_cases(user_id,history_entry_id,scope,request,ai_verdict,ai_reasoning,accuracy,industry) VALUES (${userId},${historyId},'Scope','Extra','out_of_scope','Extra','debatable','Design')`
    }
    expect((await projectRoute.DELETE(request('DELETE'), context(projectId))).status).toBe(200)
    expect((await detail.GET(request('GET'), context(created.draft.id))).status).toBe(404)
    expect(await sql`SELECT id FROM projects`).toEqual([{ id: secondProject }])
    expect(await sql`SELECT id FROM history_entries`).toEqual([{ id: secondHistory.id }])
    expect(await sql`SELECT id FROM drafts WHERE project_id = ${projectId}`).toHaveLength(0)
    expect(await sql`SELECT id FROM drafts WHERE project_id = ${secondProject}`).toHaveLength(1)
    expect(await sql`SELECT id FROM evaluation_cases WHERE history_entry_id = ${created.entry.id}`).toHaveLength(0)
    expect(await sql`SELECT id FROM evaluation_cases WHERE history_entry_id = ${secondHistory.id}`).toHaveLength(1)
    expect(await sql`SELECT id FROM evaluation_cases WHERE history_entry_id IS NULL`).toHaveLength(1)
  })

})
