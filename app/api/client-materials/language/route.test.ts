import { beforeEach, describe, expect, it, vi } from 'vitest'
import { germanLabels } from '@/lib/change-order/german-fixture'
import { ERROR_CODES } from '@/lib/api/errors'

const mocks = vi.hoisted(() => ({ user: vi.fn(), locale: vi.fn(), project: vi.fn(), allow: vi.fn(), regenerate: vi.fn(), analyze: vi.fn() }))
vi.mock('next-intl/server', () => ({ getLocale: mocks.locale }))
vi.mock('@/lib/auth/current-user', () => ({ getCurrentUser: mocks.user }))
vi.mock('@/lib/projects/data', () => ({ loadProjectForUser: mocks.project }))
vi.mock('@/lib/llm/rate-limit', () => ({ allowAnalyze: mocks.allow }))
vi.mock('@/lib/llm/client-materials', () => ({ regenerateClientMaterials: mocks.regenerate }))
vi.mock('@/lib/llm/openai', async (original) => ({ ...await original<typeof import('@/lib/llm/openai')>(), analyzeWithOpenAI: mocks.analyze }))
import { POST } from './route'

const analysis = { verdict: 'out_of_scope', confidence: 85, summary: 'Extra page', reasoning: 'Not included', citations: ['Five pages'], suggestion: 'Get approval', replies: { warm: 'Hello', neutral: 'Extra page', firm: 'Approve' }, clientLanguage: 'en', hasAdditionalWork: true, changeOrder: { description: 'Extra page', timelineImpact: 'Two days', additionalCost: '200', estimatedHours: 2, currency: 'EUR', rationale: 'Extra', note: 'Draft' } }
const history = { id: 'h1', request: 'Add a page', verdict: 'out_of_scope', summary: 'Extra page' }
const project = { scope: 'Five pages', industry: 'Development', history: [history] }
const body = { projectId: 'p1', historyId: 'h1', request: 'Add a page', clientLanguage: 'DE', analysis }
const materials = { clientLanguage: 'de', replies: { warm: 'Danke', neutral: 'Neue Seite', firm: 'Bitte genehmigen' }, changeOrder: { description: 'Neue Seite', timelineImpact: 'Zwei Tage', rationale: 'Zusätzliche Leistung', note: 'Entwurf' }, changeOrderLabels: germanLabels }
const request = (data: unknown = body) => new Request('http://localhost/api/client-materials/language', { method: 'POST', body: JSON.stringify(data) })
beforeEach(() => {
  vi.clearAllMocks()
  mocks.user.mockResolvedValue({ id: 'u1' })
  mocks.locale.mockResolvedValue('en')
  mocks.project.mockResolvedValue(project)
  mocks.allow.mockReturnValue(true)
  mocks.regenerate.mockResolvedValue(materials)
})

describe('client-material language route', () => {
  it('regenerates temporary materials before any history entry exists', async () => {
    mocks.project.mockResolvedValue({ ...project, history: [] })
    const temporary = { ...body } as Record<string, unknown>
    delete temporary.historyId
    const response = await POST(request(temporary))
    expect(response.status).toBe(200)
    expect((await response.json()).materials.clientLanguage).toBe('de')
  })
  it('translates established material without performing scope analysis or requiring commercial terms', async () => {
    const response = await POST(request())
    expect(response.status).toBe(200)
    expect(await response.json()).toEqual({ materials })
    expect(mocks.project).toHaveBeenCalledWith('p1', 'u1')
    expect(mocks.regenerate).toHaveBeenCalledWith(expect.objectContaining({ locale: 'en', clientLanguage: 'de', scope: project.scope, analysis: expect.objectContaining({ verdict: 'out_of_scope', confidence: 85, hasAdditionalWork: true, changeOrder: expect.objectContaining({ additionalCost: '200', currency: 'EUR' }) }) }))
    expect(mocks.analyze).not.toHaveBeenCalled()
  })
  it('supports ordinary included-work replies without generating a Change Order', async () => {
    mocks.project.mockResolvedValue({ ...project, history: [{ ...history, verdict: 'in_scope' }] })
    mocks.regenerate.mockResolvedValue({ ...materials, changeOrder: null })
    const response = await POST(request({ ...body, analysis: { ...analysis, verdict: 'in_scope', hasAdditionalWork: false } }))
    expect(response.status).toBe(200)
    expect((await response.json()).materials.changeOrder).toBeNull()
    expect(mocks.analyze).not.toHaveBeenCalled()
  })
  it('requires authentication and project ownership', async () => {
    mocks.user.mockResolvedValue(null)
    expect((await POST(request())).status).toBe(401)
    expect(mocks.project).not.toHaveBeenCalled()
    mocks.user.mockResolvedValue({ id: 'u1' })
    mocks.project.mockResolvedValue(null)
    expect((await POST(request())).status).toBe(404)
  })
  it.each(['ar', 'ja', 'zh', 'he', 'th', 'en-Arab'])('rejects unsupported %s before generation', async (clientLanguage) => {
    const response = await POST(request({ ...body, clientLanguage }))
    expect(response.status).toBe(400)
    expect(await response.json()).toEqual({ error: ERROR_CODES.clientLanguageUnsupported })
    expect(mocks.regenerate).not.toHaveBeenCalled()
  })
  it('rejects context that does not belong to the established history entry', async () => {
    expect((await POST(request({ ...body, historyId: 'another' }))).status).toBe(400)
    expect((await POST(request({ ...body, request: 'Different request' }))).status).toBe(400)
    expect((await POST(request({ ...body, analysis: { ...analysis, verdict: 'in_scope' } }))).status).toBe(400)
    expect(mocks.regenerate).not.toHaveBeenCalled()
  })
  it('rate limits generation', async () => {
    mocks.allow.mockReturnValue(false)
    expect((await POST(request())).status).toBe(429)
    expect(mocks.regenerate).not.toHaveBeenCalled()
  })
})
