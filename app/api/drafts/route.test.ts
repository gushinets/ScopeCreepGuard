
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { issueDraftProof } from '@/lib/drafts/proof'
import { analysisFixture, documentFixture, projectSnapshotFixture } from '@/lib/drafts/fixtures'
import type { CreateDraftInput } from '@/lib/drafts/types'
const mocks = vi.hoisted(() => ({ userId: '10000000-0000-4000-8000-000000000001', create: vi.fn() }))
vi.mock('@/lib/auth/current-user', () => ({ getCurrentUser: async () => ({ id: mocks.userId }) }))
vi.mock('@/lib/drafts/data', () => ({ createDraftForUser: mocks.create, listDraftsForUser: async () => [] }))
import { POST } from './route'

const owner = '10000000-0000-4000-8000-000000000001'
const claims = { userId: owner, projectId: '10000000-0000-4000-8000-000000000002', request: 'Add another page', locale: 'en' as const, analysisSnapshot: analysisFixture, projectSnapshot: projectSnapshotFixture }
let proof: string
const envelope = { projectId: claims.projectId, request: claims.request, locale: claims.locale, idempotencyKey: '10000000-0000-4000-8000-000000000003', draftDocument: documentFixture }
const request = (overrides: Record<string, unknown> = {}) => new Request('http://localhost/api/drafts', { method: 'POST', body: JSON.stringify({ ...envelope, proof, ...overrides }) })
beforeEach(async () => {
  vi.stubEnv('AUTH_SECRET', 'route-test-secret-with-at-least-32-characters')
  mocks.userId = owner
  mocks.create.mockReset()
  mocks.create.mockImplementation(async (_userId: string, input: CreateDraftInput) => ({
    created: true, draft: { id: 'draft-id', ...input }, entry: { id: 'history-id', verdict: input.analysisSnapshot.verdict },
  }))
  proof = await issueDraftProof(claims)
})
afterEach(() => { vi.unstubAllEnvs(); vi.useRealTimers() })
it('creates from verified server claims while preserving editable state', async () => {
  const response = await POST(request())
  expect(response.status).toBe(201)
  const { draft } = await response.json()
  expect(draft.analysisSnapshot).toEqual(analysisFixture)
  expect(draft.projectSnapshot).toEqual(projectSnapshotFixture)
  expect(draft.draftDocument.reply.text).toBe('My edited reply')
})
it('cannot substitute browser-provided immutable snapshots', async () => {
  const response = await POST(request({
    analysisSnapshot: { ...analysisFixture, verdict: 'in_scope', reasoning: 'Invented reasoning', citations: ['Invented'], replies: { warm: 'Forged', neutral: 'Forged', firm: 'Forged' }, changeOrder: { ...analysisFixture.changeOrder, additionalCost: '9999' } },
    projectSnapshot: { ...projectSnapshotFixture, scope: 'Forged scope' },
  }))
  expect(response.status).toBe(201)
  const { draft } = await response.json()
  expect(draft.analysisSnapshot).toEqual(analysisFixture)
  expect(draft.projectSnapshot).toEqual(projectSnapshotFixture)
})
it.each([
  { projectId: '10000000-0000-4000-8000-000000000009' },
  { request: 'A different request' }, { locale: 'ru' }, { proof: 'malformed' }, { proof: undefined },
])('rejects untrusted proof/bindings before entering persistence', async (override) => {
  const response = await POST(request(override))
  expect(response.status).toBe(400)
  expect(await response.json()).toEqual({ error: 'errors.draftProofInvalid' })
  expect(mocks.create).not.toHaveBeenCalled()
})
it('rejects a proof belonging to another authenticated user', async () => {
  mocks.userId = '10000000-0000-4000-8000-000000000008'
  expect((await POST(request())).status).toBe(400)
  expect(mocks.create).not.toHaveBeenCalled()
})
it('rejects an expired proof before entering persistence', async () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date(Date.now() + 3601_000))
  expect((await POST(request())).status).toBe(400)
  expect(mocks.create).not.toHaveBeenCalled()
})
it('retains retry keys and returns an already-created draft without replacing its snapshot', async () => {
  mocks.create.mockImplementation(async (_userId: string, input: CreateDraftInput) => ({
    created: false, draft: { id: 'existing-draft', analysisSnapshot: input.analysisSnapshot, projectSnapshot: input.projectSnapshot },
    entry: { id: 'existing-history' },
  }))
  const response = await POST(request())
  expect(response.status).toBe(200)
  expect((await response.json()).draft.id).toBe('existing-draft')
  expect(mocks.create).toHaveBeenCalledWith(owner, expect.objectContaining({ idempotencyKey: envelope.idempotencyKey, analysisSnapshot: analysisFixture }))
})
