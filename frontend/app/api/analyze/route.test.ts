
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { analysisFixture, projectSnapshotFixture } from '@/lib/drafts/fixtures'
import { verifyDraftProof } from '@/lib/drafts/proof'
const project = { id: '10000000-0000-4000-8000-000000000002', ...projectSnapshotFixture, history: [] }
const userId = '10000000-0000-4000-8000-000000000001'
const mocks = vi.hoisted(() => ({ analyze: vi.fn(), project: vi.fn() }))
vi.mock('@/lib/auth/current-user', () => ({ getCurrentUser: async () => ({ id: '10000000-0000-4000-8000-000000000001' }) }))
vi.mock('@/lib/projects/data', () => ({ loadProjectForUser: mocks.project }))
vi.mock('next-intl/server', () => ({ getLocale: async () => 'en' }))
vi.mock('@/lib/llm/rate-limit', () => ({ allowAnalyze: () => true }))
vi.mock('@/lib/llm/openai', () => ({ analyzeWithOpenAI: mocks.analyze, analyzeFailureResponse: () => ({ error: 'errors.analysisInvalid', status: 502 }) }))
import { POST } from './route'
beforeEach(() => {
  vi.stubEnv('AUTH_SECRET', 'analysis-test-secret-with-at-least-32-characters')
  mocks.project.mockResolvedValue(structuredClone(project))
  mocks.analyze.mockResolvedValue(structuredClone(analysisFixture))
})
afterEach(() => { vi.unstubAllEnvs(); vi.clearAllMocks() })
it('issues a proof binding the validated result to the exact model project inputs', async () => {
  const response = await POST(new Request('http://localhost/api/analyze', {
    method: 'POST', body: JSON.stringify({ projectId: project.id, request: 'Add a page', endDate: '2026-12-01', documentLanguage: 'en' }),
  }))
  expect(response.status).toBe(200)
  const body = await response.json()
  const claims = await verifyDraftProof(body.proof, { userId, projectId: project.id, request: 'Add a page', locale: 'en' })
  expect(claims.analysisSnapshot).toEqual(body.result)
  expect(claims.projectSnapshot).toEqual({ ...projectSnapshotFixture, endDate: '2026-12-01', documentLanguage: 'en' })
  expect(body.projectSnapshot).toEqual(claims.projectSnapshot)
  expect(response.headers.get('Cache-Control')).toBe('private, no-store')
  expect(mocks.analyze).toHaveBeenCalledWith(expect.objectContaining({
    scope: 'Build exactly five pages. Further pages are outside the agreed scope.',
    startDate: '2026-01-01', endDate: '2026-12-01', pricingModel: 'hourly',
    currency: 'EUR', hourlyRate: '100.00', fixedPrice: null, documentLanguage: 'en',
  }))
})
it('does not issue a proof for invalid model output', async () => {
  mocks.analyze.mockResolvedValue({ ...analysisFixture, confidence: -1 })
  const response = await POST(new Request('http://localhost/api/analyze', { method: 'POST', body: JSON.stringify({ projectId: project.id, request: 'Add a page' }) }))
  expect(response.status).toBe(502)
  expect(await response.json()).not.toHaveProperty('proof')
})
