import { vi } from 'vitest'
import { analysisFixture, documentFixture } from '@/features/drafts/model/fixtures'
import type { WorkingDraft } from '@/features/drafts'
import type { PersistentProject } from '@/features/projects'
import { applyUserPatch } from '@/features/drafts/model/user-patch'

/** HTTP fixture for client integration tests only. Real server rules are tested with PostgreSQL. */
export function workflowFixture() {
  const project: PersistentProject = { id: 'p1', name: 'Website', clientName: 'Server client', clientEmail: 'client@example.test', endDate: '2026-12-01', industry: 'Design', scope: 'Build five pages', startDate: '2026-10-01', pricingModel: 'hourly', currency: 'EUR', hourlyRate: '100.00', fixedPrice: null, history: [] }
  const draft: WorkingDraft = { id: 'd1', projectId: 'p1', revision: '3', requestText: 'Add a page', lastAnalysisRunId: 'a1', analysisIsStale: false,
    draftDocument: { version: 2, reply: { ...documentFixture.reply, language: 'es' }, changeOrder: structuredClone(documentFixture.changeOrder), languageSelection: { language: 'es', confidence: 0.99, status: 'detected', selectedLanguage: 'es', override: true, version: 'fixture', requestHash: 'request' } },
    analysisRun: { id: 'a1', projectId: 'p1', sourceDraftId: 'd1', sourceDraftRevision: '2', requestText: 'Add a page', projectSnapshot: structuredClone(project), interfaceLocale: 'en', resultSnapshot: structuredClone(analysisFixture), status: 'succeeded', finishedAt: '2026-10-19T12:00:00Z' }, createdAt: '2026-10-19T10:00:00Z', updatedAt: '2026-10-19T12:00:00Z' }
  const state = { projects: [project], drafts: new Map([['d1', draft]]), owner: 'u1', calls: [] as { path: string; method: string; body: Record<string, unknown> }[], failure: '' }
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input), method = init?.method ?? 'GET'
    const body = init?.body ? JSON.parse(String(init.body)) as Record<string, unknown> : {}
    state.calls.push({ path, method, body })
    if (state.failure && path.includes(state.failure)) return Response.json({ error: 'errors.requestFailed' }, { status: 503 })
    if (path === '/api/auth/me') return state.owner ? Response.json({ user: { id: state.owner, email: 'owner@example.test' } }) : Response.json({ error: 'errors.authRequired' }, { status: 401 })
    if (path === '/api/auth/logout') { state.owner = ''; return Response.json({ ok: true }) }
    if (path === '/api/locale') { document.cookie = `locale=${body.locale}; Path=/`; return Response.json({ ok: true }) }
    if (path === '/api/v2/projects' && method === 'GET') return Response.json({ projects: state.projects })
    if (path === '/api/v2/projects' && method === 'POST') {
      const next = { ...project, ...body, id: 'p2', history: [] } as PersistentProject
      state.projects.push(next); state.drafts.set('d2', { ...structuredClone(draft), id: 'd2', projectId: 'p2', analysisRun: null, lastAnalysisRunId: null })
      return Response.json({ project: next })
    }
    const projectId = /^\/api\/v2\/projects\/([^/]+)$/.exec(path)?.[1]
    if (projectId && method === 'PATCH') {
      const existing = state.projects.find(item => item.id === projectId)!
      Object.assign(existing, body)
      return Response.json({ project: existing })
    }
    if (projectId && method === 'DELETE') { state.projects = state.projects.filter(item => item.id !== projectId); return Response.json({ ok: true }) }
    const forProject = /^\/api\/v2\/projects\/([^/]+)\/draft$/.exec(path)?.[1]
    const id = /^\/api\/v2\/drafts\/([^/]+)/.exec(path)?.[1]
    const current = forProject ? [...state.drafts.values()].find(item => item.projectId === forProject) : id ? state.drafts.get(id) : null
    if (!current) return Response.json({ error: 'errors.draftNotFound' }, { status: 404 })
    if (method === 'PUT') {
      const next = { ...applyUserPatch(current, body.patch as Record<string, string | boolean>), revision: String(BigInt(current.revision) + 1n) }
      state.drafts.set(current.id, next); return Response.json({ draft: next })
    }
    if (method === 'POST' && path.endsWith('/translate')) {
      current.draftDocument.reply.language = String(body.language)
      current.draftDocument.languageSelection = { ...current.draftDocument.languageSelection!, override: true, selectedLanguage: String(body.language) }
      current.revision = String(BigInt(current.revision) + 1n)
    }
    if (method === 'POST' && path.endsWith('/regenerate')) {
      const tone = current.draftDocument.reply.tone
      current.draftDocument.reply.generated[tone] = 'Regenerated selected reply'
      current.draftDocument.reply.text = 'Regenerated selected reply'
      current.revision = String(BigInt(current.revision) + 1n)
    }
    return Response.json({ draft: current })
  })
  vi.stubGlobal('fetch', fetcher)
  return { state, project, draft, fetcher }
}
