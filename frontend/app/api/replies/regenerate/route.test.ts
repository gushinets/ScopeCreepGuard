import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ERROR_CODES } from '@/lib/api/errors'

const {
  allowAnalyzeMock,
  getCurrentUserMock,
  getLocaleMock,
  loadProjectForUserMock,
  regenerateReplyWithOpenAIMock,
} = vi.hoisted(() => ({
  allowAnalyzeMock: vi.fn(),
  getCurrentUserMock: vi.fn(),
  getLocaleMock: vi.fn(),
  loadProjectForUserMock: vi.fn(),
  regenerateReplyWithOpenAIMock: vi.fn(),
}))

vi.mock('next-intl/server', () => ({ getLocale: getLocaleMock }))
vi.mock('@/lib/auth/current-user', () => ({
  getCurrentUser: getCurrentUserMock,
}))
vi.mock('@/lib/projects/data', () => ({
  loadProjectForUser: loadProjectForUserMock,
}))
vi.mock('@/lib/llm/rate-limit', () => ({ allowAnalyze: allowAnalyzeMock }))
vi.mock('@/lib/llm/openai', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/lib/llm/openai')>()
  return {
    ...original,
    regenerateReplyWithOpenAI: regenerateReplyWithOpenAIMock,
  }
})

import { POST } from './route'

const body = {
  projectId: 'project-1',
  request: 'Please add a blog.',
  tone: 'firm',
  previousReply: 'The blog is outside the agreed scope.',
}

const project = {
  id: 'project-1',
  name: 'Website',
  industry: 'Development',
  scope: 'Build a five-page marketing website.',
  history: [],
}

function request(value: unknown = body) {
  return new Request('http://localhost/api/replies/regenerate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(value),
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  getCurrentUserMock.mockResolvedValue({ id: 'user-1', email: 'user@example.com' })
  getLocaleMock.mockResolvedValue('en')
  loadProjectForUserMock.mockResolvedValue(project)
  allowAnalyzeMock.mockReturnValue(true)
  regenerateReplyWithOpenAIMock.mockResolvedValue('A newly generated firm reply.')
})

describe('POST /api/replies/regenerate', () => {
  it('returns 401 before reading project data when unauthenticated', async () => {
    getCurrentUserMock.mockResolvedValue(null)

    const response = await POST(request())

    expect(response.status).toBe(401)
    await expect(response.json()).resolves.toEqual({ error: ERROR_CODES.authRequired })
    expect(loadProjectForUserMock).not.toHaveBeenCalled()
  })

  it('returns 400 for an invalid request body', async () => {
    const response = await POST(request({ ...body, tone: 'casual' }))

    expect(response.status).toBe(400)
    await expect(response.json()).resolves.toEqual({
      error: ERROR_CODES.requestBodyInvalid,
    })
    expect(loadProjectForUserMock).not.toHaveBeenCalled()
  })

  it('returns 404 for a missing or inaccessible project', async () => {
    loadProjectForUserMock.mockResolvedValue(null)

    const response = await POST(request())

    expect(response.status).toBe(404)
    await expect(response.json()).resolves.toEqual({
      error: ERROR_CODES.projectNotFound,
    })
    expect(regenerateReplyWithOpenAIMock).not.toHaveBeenCalled()
  })

  it('checks project ownership with the authenticated user id', async () => {
    await POST(request())

    expect(loadProjectForUserMock).toHaveBeenCalledWith('project-1', 'user-1')
  })

  it('rejects an unsupported interface locale', async () => {
    getLocaleMock.mockResolvedValue('de')

    const response = await POST(request())

    expect(response.status).toBe(400)
    await expect(response.json()).resolves.toEqual({
      error: ERROR_CODES.localeInvalid,
    })
    expect(regenerateReplyWithOpenAIMock).not.toHaveBeenCalled()
  })

  it('loads server project data and returns only the regenerated reply', async () => {
    const response = await POST(request())

    expect(response.status).toBe(200)
    await expect(response.json()).resolves.toEqual({
      reply: 'A newly generated firm reply.',
    })
    expect(regenerateReplyWithOpenAIMock).toHaveBeenCalledWith({
      scope: project.scope,
      request: body.request,
      industry: project.industry,
      locale: 'en',
      tone: 'firm',
      previousReply: body.previousReply,
    })
  })
})
