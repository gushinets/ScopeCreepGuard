import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ERROR_CODES } from '@/lib/api/errors'

const mocks = vi.hoisted(() => ({ user: vi.fn(), locale: vi.fn(), project: vi.fn(), allow: vi.fn(), analyze: vi.fn() }))
vi.mock('next-intl/server', () => ({ getLocale: mocks.locale }))
vi.mock('@/lib/auth/current-user', () => ({ getCurrentUser: mocks.user }))
vi.mock('@/lib/projects/data', () => ({ loadProjectForUser: mocks.project }))
vi.mock('@/lib/llm/rate-limit', () => ({ allowAnalyze: mocks.allow }))
vi.mock('@/lib/llm/openai', async (original) => ({ ...await original<typeof import('@/lib/llm/openai')>(), analyzeWithOpenAI: mocks.analyze }))
import { POST } from './route'

const project = { id: 'p1', industry: 'Development', scope: 'Five pages', startDate: '2026-01-01', pricingModel: 'hourly', currency: 'EUR', hourlyRate: '100', fixedPrice: null }
const result = { verdict: 'out_of_scope', hasAdditionalWork: true, estimateValid: true, changeOrder: { currency: 'EUR' } }
const request = (documentLanguage?: string) => new Request('http://localhost/api/change-orders/estimate', { method: 'POST', body: JSON.stringify({ projectId: 'p1', request: 'Add a page', ...(documentLanguage ? { documentLanguage } : {}) }) })
beforeEach(() => {
  vi.clearAllMocks()
  mocks.user.mockResolvedValue({ id: 'u1' })
  mocks.locale.mockResolvedValue('en')
  mocks.project.mockResolvedValue(project)
  mocks.allow.mockReturnValue(true)
  mocks.analyze.mockResolvedValue({ ...result })
})

describe('Change Order estimate guards', () => {
  it.each([undefined, 'de'])('requires complete commercial terms with override %s', async (override) => {
    mocks.project.mockResolvedValue({ ...project, hourlyRate: null })
    const response = await POST(request(override))
    expect(response.status).toBe(400)
    expect(await response.json()).toEqual({ error: ERROR_CODES.pricingModelInvalid })
    expect(mocks.analyze).not.toHaveBeenCalled()
  })
  it.each([undefined, 'de'])('rejects included work with override %s', async (override) => {
    mocks.analyze.mockResolvedValue({ ...result, verdict: 'in_scope', hasAdditionalWork: false })
    expect((await POST(request(override))).status).toBe(409)
  })
  it('requires additional work, a valid estimate and matching currency even with an override', async () => {
    mocks.analyze.mockResolvedValue({ ...result, hasAdditionalWork: false })
    expect((await POST(request('de'))).status).toBe(409)
    mocks.analyze.mockResolvedValue({ ...result, estimateValid: false })
    expect((await POST(request('de'))).status).toBe(502)
    mocks.analyze.mockResolvedValue({ ...result, changeOrder: { currency: 'USD' } })
    expect((await POST(request('de'))).status).toBe(502)
  })
})
