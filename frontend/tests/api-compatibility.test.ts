/** Real TS handlers + real Drizzle against a harness-owned disposable database. */
import { readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import postgres from 'postgres'
import { drizzle } from 'drizzle-orm/postgres-js'
import { afterEach, expect, it, vi } from 'vitest'
import { decodeJwt } from 'jose'
import { NextRequest } from 'next/server'
import { analysisFixture, documentFixture } from '@/lib/drafts/fixtures'
import * as schema from '@/lib/db/schema'
import { ERROR_CODES } from '@/lib/api/errors'

vi.mock('server-only', () => ({}))

const state = vi.hoisted(() => ({
  user: null as { id: string; email: string } | null,
  result: {} as unknown, calls: 0, locale: 'en',
}))
vi.mock('@/lib/auth/current-user', () => ({ getCurrentUser: async () => state.user }))
vi.mock('next-intl/server', () => ({ getLocale: async () => state.locale }))

afterEach(() => { vi.useRealTimers(); vi.unstubAllEnvs(); vi.restoreAllMocks() })

type Handler = (request: NextRequest, context: { params: Promise<{ id: string }> }) => Promise<Response>
type Operation = { method: string; path: string; handler: Handler }
const fixtureFile = resolve('../contracts/compatibility/any-640/http.json')

it.skipIf(!process.env.SCG_COMPATIBILITY_DATABASE_URL)('freezes all 21 HTTP operations, errors and persistence effects', async () => {
  const url = new URL(process.env.SCG_COMPATIBILITY_DATABASE_URL!)
  if (!['127.0.0.1', 'localhost'].includes(url.hostname) || url.username !== 'scg_test' ||
    !/^scg_test_[0-9a-f]{32}$/.test(url.pathname.slice(1)) || url.search) throw new Error('Disposable target required')
  const sql = postgres(url.toString(), { max: 5, onnotice: () => {} })
  vi.doMock('@/lib/db', () => ({ db: drizzle(sql, { schema }) }))
  vi.stubEnv('AUTH_SECRET', 'any640-synthetic-contract-secret-at-least-32-characters')
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-10-10T09:00:00.000Z'))
  vi.spyOn(console, 'error').mockImplementation(() => {})
  state.result = structuredClone(analysisFixture)
  const aliases = new Map<string, string>()
  const aliasesIn = (value: unknown): unknown => {
    if (typeof value === 'string') return aliases.get(value) ?? value
    if (Array.isArray(value)) return value.map(aliasesIn)
    if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, aliasesIn(child)]))
    return value
  }
  const normalize = (value: unknown) => JSON.parse(JSON.stringify(aliasesIn(value)))
  const observations: unknown[] = []
  const errors: unknown[] = []
  const ids = { project: '', history: '', draft: '' }
  const operations: Operation[] = []
  let cookie = ''

  async function rows() {
    const [row] = await sql`SELECT
      (SELECT count(*)::int FROM users) AS users,
      (SELECT count(*)::int FROM projects) AS projects,
      (SELECT count(*)::int FROM history_entries) AS history,
      (SELECT count(*)::int FROM drafts) AS drafts,
      (SELECT count(*)::int FROM evaluation_cases) AS evaluations`
    const checked = await sql`SELECT id,last_checked FROM projects ORDER BY id`
    const snapshots = await sql`SELECT id,analysis_snapshot,project_snapshot FROM drafts ORDER BY id`
    return { counts: row, checked: JSON.stringify(checked), snapshots: JSON.stringify(snapshots) }
  }

  async function invoke(operation: Operation, body?: unknown) {
    return operation.handler(new NextRequest(`http://contract.test${operation.path.replace('{id}', ids.project).replace('{draftId}', ids.draft)}`, {
      method: operation.method, headers: { 'content-type': 'application/json', ...(cookie && state.user ? { cookie } : {}) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    }), { params: Promise.resolve({ id: operation.path.includes('{draftId}') ? ids.draft : ids.project }) })
  }

  async function capture(method: string, path: string, module: Record<string, unknown>, body?: unknown,
    options: { status?: number; alias?: [string, string]; delta?: Record<string, number>; llm?: number } = {}) {
    const operation = { method, path, handler: module[method] as Handler }
    operations.push(operation)
    const before = await rows()
    const calls = (await (await fetch(process.env.SCOPE_GUARD_API_ORIGIN + '/__generation_calls')).json()).calls
    const response = await invoke(operation, body)
    expect(response.status).toBe(options.status ?? 200)
    const raw = await response.text()
    const json = response.headers.get('content-type')?.startsWith('application/json') ? JSON.parse(raw) : undefined
    if (options.alias && json) {
      let value = json
      for (const key of options.alias[0].split('.')) value = value[key]
      aliases.set(value, options.alias[1])
    }
    if (json?.proof) aliases.set(json.proof, '$proof')
    if (response.headers.get('set-cookie')?.startsWith('scg_session=')) {
      const token = response.headers.getSetCookie()[0].split(';')[0].slice('scg_session='.length)
      if (token) {
        aliases.set(token, '$session')
        cookie = `scg_session=${token}; locale=en`
      }
    }
    state.calls = (await (await fetch(process.env.SCOPE_GUARD_API_ORIGIN + '/__generation_calls')).json()).calls
    const after = await rows()
    const delta = Object.fromEntries(Object.keys(before.counts).map((key) => [key, after.counts[key] - before.counts[key]]))
    expect(delta).toEqual({ users: 0, projects: 0, history: 0, drafts: 0, evaluations: 0, ...options.delta })
    expect(state.calls - calls).toBe(options.llm ?? 0)
    const headers = Object.fromEntries(['content-type', 'cache-control', 'content-disposition'].flatMap((name) => {
      const value = response.headers.get(name)
      return value === null ? [] : [[name, value]]
    }))
    const cookies = response.headers.getSetCookie().map((value) => {
      for (const [actual, alias] of aliases) value = value.replace(actual, alias)
      return value
    })
    observations.push({ method, path, request: normalize(body ?? null), status: response.status,
      ...(json === undefined ? { text: raw } : { body: normalize(json) }), headers, cookies,
      effects: { rows: delta, lastCheckedChanged: before.checked !== after.checked,
        immutableSnapshotsChanged: before.snapshots !== after.snapshots, llmCalls: state.calls - calls } })
    return json
  }

  try {
    const register = await import('@/app/api/auth/register/route')
    const login = await import('@/app/api/auth/login/route')
    const me = await import('@/app/api/auth/me/route')
    const logout = await import('@/app/api/auth/logout/route')
    const projects = await import('@/app/api/projects/route')
    const project = await import('@/app/api/projects/[id]/route')
    const history = await import('@/app/api/projects/[id]/history/route')
    const analyze = await import('@/app/api/analyze/route')
    const reply = await import('@/app/api/replies/regenerate/route')
    const language = await import('@/app/api/client-materials/language/route')
    const estimate = await import('@/app/api/change-orders/estimate/route')
    const drafts = await import('@/app/api/drafts/route')
    const draft = await import('@/app/api/drafts/[id]/route')
    const evaluation = await import('@/app/api/evaluations/route')
    const exported = await import('@/app/api/evaluations/export/route')
    const locale = await import('@/app/api/locale/route')

    const credentials = { email: ' Owner@Example.Test ', password: 'synthetic-password' }
    const registered = await capture('POST', '/api/auth/register', register, credentials,
      { status: 201, alias: ['user.id', '$user'], delta: { users: 1 } })
    state.user = registered.user
    await capture('POST', '/api/auth/login', login, credentials)
    await capture('GET', '/api/auth/me', me)
    const card = { name: ' Website ', clientName: ' Acme ', industry: 'Development',
      scope: 'Five pages only.', startDate: '2026-01-01', pricingModel: 'hourly', currency: 'EUR',
      hourlyRate: '100', fixedPrice: 'ignored', clientEmail: 'browser@example.test', endDate: '2026-12-01' }
    const created = await capture('POST', '/api/projects', projects, card,
      { status: 201, alias: ['project.id', '$project'], delta: { projects: 1 } })
    ids.project = created.project.id
    await capture('GET', '/api/projects', projects)
    await capture('GET', '/api/projects/{id}', project)
    const edited = { ...card, name: 'Renamed', hourlyRate: '125.10' } as Record<string, unknown>
    delete edited.clientName
    const patched = await capture('PATCH', '/api/projects/{id}', project, edited)
    expect(patched.project.clientName).toBe('Acme')
    const analysis = await capture('POST', '/api/analyze', analyze,
      { projectId: ids.project, request: 'Add another page', endDate: '2026-12-01', documentLanguage: 'en' }, { llm: 1 })
    expect((await rows()).counts.history).toBe(0)
    expect(normalize(decodeJwt(analysis.proof))).toMatchObject({ version: 'scg-draft-proof-v1',
      userId: '$user', projectId: '$project', request: 'Add another page', locale: 'en' })
    await capture('POST', '/api/replies/regenerate', reply,
      { projectId: ids.project, request: 'Add another page', tone: 'firm', previousReply: 'Old reply', documentLanguage: 'en' }, { llm: 1 })
    const generation = { projectId: ids.project, request: 'Add another page', proof: analysis.proof, locale: 'en' }
    await capture('POST', '/api/client-materials/language', language,
      { ...generation, clientLanguage: 'en', analysis: analysis.result }, { llm: 1 })
    await capture('POST', '/api/change-orders/estimate', estimate,
      { ...generation, endDate: '2026-12-01', documentLanguage: 'en' }, { llm: 1 })
    const document = { ...structuredClone(documentFixture), result: analysis.result }
    const saved = await capture('POST', '/api/drafts', drafts,
      { ...generation, idempotencyKey: '10000000-0000-4000-8000-000000000004', draftDocument: document },
      { status: 201, alias: ['draft.id', '$draft'], delta: { history: 1, drafts: 1 } })
    // First save needs both linked identifiers normalized in the stored observation.
    ids.draft = saved.draft.id; ids.history = saved.entry.id
    aliases.set(ids.history, '$history')
    observations[observations.length - 1] = normalize(observations[observations.length - 1])
    await capture('GET', '/api/drafts', drafts)
    await capture('GET', '/api/drafts/{draftId}', draft)
    document.reply.text = 'Edited Русский reply'
    await capture('PUT', '/api/drafts/{draftId}', draft, { draftDocument: document })
    const entry = await capture('POST', '/api/projects/{id}/history', history,
      { date: '2026-10-08', request: 'Legacy request', verdict: 'borderline', summary: 'Legacy summary' },
      { status: 201, alias: ['entry.id', '$legacyHistory'], delta: { history: 1 } })
    expect(entry.entry).not.toHaveProperty('projectId')
    await capture('POST', '/api/evaluations', evaluation,
      { historyEntryId: ids.history, accuracy: 'wrong', aiReasoning: 'Recorded reasoning', humanVerdict: 'in_scope' },
      { alias: ['evaluation.id', '$evaluation'], delta: { evaluations: 1 } })
    await capture('GET', '/api/evaluations/export', exported)
    await capture('POST', '/api/locale', locale, { locale: 'ru' })
    await capture('POST', '/api/auth/logout', logout)

    // Characterize every protected operation before deletion, including mutations.
    state.user = null
    for (const operation of [...operations, { method: 'DELETE', path: '/api/projects/{id}', handler: project.DELETE }].filter((op) => !['/api/auth/register', '/api/auth/login', '/api/auth/logout', '/api/locale'].includes(op.path))) {
      const response = await invoke(operation)
      expect(response.status).toBe(401)
      expect(await response.json()).toEqual({ error: 'errors.authRequired' })
      errors.push({ method: operation.method, path: operation.path, scenario: 'unauthenticated', status: 401, body: { error: 'errors.authRequired' } })
    }
    state.user = registered.user
    const failureCases = [
      { method: 'POST', path: '/api/auth/register', handler: register.POST,
        request: { email: 'owner@example.test', password: 'synthetic-password' },
        status: 409, error: ERROR_CODES.duplicateEmail, scenario: 'duplicate_email' },
      { method: 'POST', path: '/api/auth/login', handler: login.POST,
        request: { email: 'owner@example.test', password: 'wrong-password' },
        status: 401, error: ERROR_CODES.invalidCredentials, scenario: 'invalid_credentials' },
      { method: 'POST', path: '/api/auth/register', handler: register.POST,
        request: {}, status: 400, error: ERROR_CODES.emailRequired, scenario: 'email_before_password' },
      { method: 'POST', path: '/api/projects', handler: projects.POST,
        request: {}, status: 400, error: ERROR_CODES.projectNameRequired, scenario: 'name_before_scope' },
    ]
    for (const failure of failureCases) {
      const before = await rows()
      const response = await invoke({ ...failure, handler: failure.handler as Handler }, failure.request)
      expect(response.status).toBe(failure.status)
      const body = await response.json()
      expect(body).toEqual({ error: failure.error })
      expect(await rows()).toEqual(before)
      errors.push({ method: failure.method, path: failure.path, scenario: failure.scenario,
        request: failure.request, status: failure.status, body })
    }
    for (const operation of operations.filter((op) => ['POST', 'PUT', 'PATCH'].includes(op.method) && op.path !== '/api/auth/logout')) {
      const response = await invoke(operation, null)
      expect(response.status).toBe(400)
      const body = await response.json()
      expect(body).toEqual({ error: 'errors.requestBodyInvalid' })
      errors.push({ method: operation.method, path: operation.path, scenario: 'null_body', request: null, status: 400, body })
    }
    await capture('DELETE', '/api/projects/{id}', project, undefined,
      { delta: { projects: -1, history: -2, drafts: -1, evaluations: -1 } })
    expect(operations).toHaveLength(21)
    const fixture = { version: 1, baseCommit: '97518baacaba56a1a2542fe145b14d62644c5fda',
      boundaries: 'Real TS handlers and Drizzle; synthetic current-user/locale and deterministic LLM adapters; signed tokens are symbolic.',
      errorCodes: Object.values(ERROR_CODES), operations: observations, errors }
    if (process.env.SCG_UPDATE_COMPATIBILITY === '1') writeFileSync(fixtureFile, JSON.stringify(fixture, null, 2) + '\n')
    expect(fixture).toEqual(JSON.parse(readFileSync(fixtureFile, 'utf8')))
  } finally {
    await sql.end()
    vi.doUnmock('@/lib/db')
  }
}, 60_000)
