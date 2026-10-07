'use client'

import { useRouter } from 'next/navigation'
import { useLocale } from 'next-intl'
import { applyClientMaterials, parseClientMaterials, type ClientMaterials } from '@/lib/client-materials'
import type { CreatedDraftResponse, DraftDocument, DraftListItem, SavedDraft, ReplyDocument, ProjectSnapshot } from '@/lib/drafts/types'
import { editableChangeOrder } from '@/lib/drafts/document'
import { mergeEstimate } from '@/lib/change-order/merge-estimate'
import type { EditableDraft } from '@/lib/change-order/document'
import type { Locale } from '@/i18n/config'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { ERROR_CODES, assertErrorCode, type ErrorCode } from '@/lib/api/errors'
import { readProjectDetails } from '@/lib/projects/browser-details'
import { projectAnalysisInputsChanged } from '@/lib/projects/analysis-inputs'
import { validISODate } from '@/lib/projects/validation'
import type {
  AnalysisResult,
  EvaluationAccuracy,
  HistoryEntry,
  Industry,
  Project,
  PricingModel,
  Currency,
  Verdict,
} from '@/lib/types'

export type View = 'check' | 'projects' | 'new_project' | 'edit_project' | 'history' | 'drafts'

export type AnalysisStatus =
  | 'idle'
  | 'loading'
  | 'result'
  | 'error'
  | 'short_scope'

interface AuthUser {
  id: string
  email: string
}

interface NewProjectInput {
  name: string
  industry: Industry
  scope: string
  startDate: string
  pricingModel: PricingModel
  currency: Currency
  hourlyRate: string
  fixedPrice: string
}

interface StoreValue {
  user: AuthUser | null
  projects: Project[]
  selectedProject: Project | null
  analysisProject: Project | null
  projectSnapshot: ProjectSnapshot | null
  selectedProjectId: string | null
  view: View
  requestText: string
  analyzedRequest: string | null
  status: AnalysisStatus
  result: AnalysisResult | null
  clientMaterials: ClientMaterials | null
  draftDocument: DraftDocument | null
  currentDraftId: string | null
  draftSessionId: string
  isSavingDraft: boolean
  draftError: ErrorCode | ''
  isDraftDirty: boolean
  saveDraft: () => Promise<void>
  openDraft: (id: string) => Promise<void>
  listDrafts: () => Promise<DraftListItem[]>
  updateChangeOrder: (draft: EditableDraft) => void
  updateReply: (reply: ReplyDocument) => void
  changeClientLanguage: (language: string) => Promise<boolean>
  currentHistoryEntryId: string | null
  analysisError: ErrorCode | ''
  isLoadingProjects: boolean
  projectError: ErrorCode | ''

  setView: (v: View) => void
  selectProject: (id: string) => void
  createProject: (input: NewProjectInput) => Promise<Project>
  updateProject: (id: string, input: NewProjectInput) => Promise<Project>
  createEstimate: (projectId: string, request: string, documentLanguage?: string) => Promise<AnalysisResult>
  setRequestText: (t: string) => void
  loadExample: (text: string) => void
  runCheck: () => void
  reset: () => void
  logout: () => Promise<void>
  submitEvaluation: (input: {
    accuracy: EvaluationAccuracy
    humanVerdict?: Verdict
  }) => Promise<void>
  downloadEvaluationsExport: () => Promise<void>
}

interface ProjectsResponse {
  projects: Project[]
}

interface ProjectResponse {
  project: Project
}

interface MeResponse {
  user: AuthUser
}

class ApiError extends Error {
  constructor(
    message: ErrorCode,
    readonly status: number,
  ) {
    super(message)
  }
}

const Ctx = createContext<StoreValue | null>(null)

async function readApiError(response: Response) {
  let body: unknown

  try {
    body = await response.json()
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'api_error_body_invalid',
        status: response.status,
        message: error instanceof Error ? error.message : 'Unknown JSON parse error',
      }),
    )
    return ERROR_CODES.requestFailed
  }

  if (
    body &&
    typeof body === 'object' &&
    !Array.isArray(body) &&
    typeof (body as Record<string, unknown>).error === 'string'
  ) {
    return assertErrorCode((body as Record<string, string>).error)
  }

  return ERROR_CODES.requestFailed
}

async function readApiSuccess<T>(response: Response): Promise<T> {
  try {
    return (await response.json()) as T
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'api_success_body_invalid',
        status: response.status,
        message: error instanceof Error ? error.message : 'Unknown JSON parse error',
      }),
    )
    throw error
  }
}

async function apiFetch<T>(input: RequestInfo | URL, init?: RequestInit) {
  let response: Response

  try {
    response = await fetch(input, init)
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'api_request_failed',
        message: error instanceof Error ? error.message : 'Unknown request error',
      }),
    )
    throw new ApiError(ERROR_CODES.requestFailed, 0)
  }

  if (!response.ok) {
    throw new ApiError(await readApiError(response), response.status)
  }

  return readApiSuccess<T>(response)
}

async function listDrafts() {
  return (await apiFetch<{ drafts: DraftListItem[] }>('/api/drafts', { cache: 'no-store' })).drafts
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const router = useRouter()
  const locale = useLocale()
  const [draftDocument, setDraftDocument] = useState<DraftDocument | null>(null)
  const [draftProof, setDraftProof] = useState<string | null>(null)
  const [projectSnapshot, setProjectSnapshot] = useState<ProjectSnapshot | null>(null)
  const [analysisSnapshot, setAnalysisSnapshot] = useState<AnalysisResult | null>(null)
  const [analysisLocale, setAnalysisLocale] = useState<Locale>('en')
  const [currentDraftId, setCurrentDraftId] = useState<string | null>(null)
  const [draftSessionId, setDraftSessionId] = useState('')
  const [isSavingDraft, setIsSavingDraft] = useState(false)
  const [draftError, setDraftError] = useState<ErrorCode | ''>('')
  const [savedSignature, setSavedSignature] = useState('')
  const savingDraft = useRef(false)
  const result = draftDocument?.result ?? null
  const clientMaterials = draftDocument?.clientMaterials ?? null
  const [user, setUser] = useState<AuthUser | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [view, changeView] = useState<View>('check')
  const draftOpenRun = useRef(0)
  const setView = useCallback((next: View) => {
    draftOpenRun.current += 1
    changeView(next)
  }, [])
  const [requestText, setRequestText] = useState('')
  const [analyzedRequest, setAnalyzedRequest] = useState<string | null>(null)
  const [status, setStatus] = useState<AnalysisStatus>('idle')
  const [currentHistoryEntryId, setCurrentHistoryEntryId] = useState<string | null>(
    null,
  )
  const [analysisError, setAnalysisError] = useState<ErrorCode | ''>('')
  const [isLoadingProjects, setIsLoadingProjects] = useState(true)
  const [projectError, setProjectError] = useState<ErrorCode | ''>('')
  const analysisRun = useRef(0)

  const restoreDraft = useCallback((draft: SavedDraft) => {
    analysisRun.current += 1
    setSelectedProjectId(draft.projectId)
    setRequestText(draft.request)
    setAnalyzedRequest(draft.request)
    setAnalysisSnapshot(draft.analysisSnapshot)
    setDraftProof(null)
    setProjectSnapshot(draft.projectSnapshot ?? null)
    setAnalysisLocale(draft.locale)
    setDraftDocument(draft.draftDocument)
    setCurrentDraftId(draft.id)
    setCurrentHistoryEntryId(draft.historyEntryId)
    setDraftSessionId(draft.id)
    setSavedSignature(JSON.stringify(draft.draftDocument))
    setAnalysisError('')
    setDraftError('')
    setStatus('result')
    setView('check')
    const url = new URL(window.location.href)
    url.searchParams.set('draft', draft.id)
    window.history.replaceState(window.history.state, '', url)
  }, [setView])

  const selectedProject =
    projects.find((p) => p.id === selectedProjectId) ?? null

  const analysisProject: Project | null = selectedProject && (projectSnapshot
    ? { ...selectedProject, ...projectSnapshot }
    : currentDraftId
      ? { ...selectedProject, name: draftDocument?.changeOrder?.projectName ?? '', scope: '', startDate: null, pricingModel: null, currency: null, hourlyRate: null, fixedPrice: null }
      : selectedProject)

  useEffect(() => {
    let isActive = true

    async function loadInitialData() {
      setIsLoadingProjects(true)
      setProjectError('')

      try {
        const [meResponse, projectsResponse] = await Promise.all([
          apiFetch<MeResponse>('/api/auth/me'),
          apiFetch<ProjectsResponse>('/api/projects'),
        ])

        if (!isActive) return

        setUser(meResponse.user)
        setProjects(projectsResponse.projects)
        setSelectedProjectId(projectsResponse.projects[0]?.id ?? null)
        const draftId = new URLSearchParams(window.location.search).get('draft')
        if (draftId !== null) {
          const openRun = ++draftOpenRun.current
          const run = analysisRun.current
          try {
            const { draft } = await apiFetch<{ draft: SavedDraft }>(`/api/drafts/${encodeURIComponent(draftId)}`, { cache: 'no-store' })
            if (!isActive || openRun !== draftOpenRun.current || run !== analysisRun.current) return
            restoreDraft(draft)
          } catch (error) {
            if (!isActive || openRun !== draftOpenRun.current || run !== analysisRun.current) return
            // A missing/foreign draft must not invalidate a loaded workspace.
            // An expired session still uses the normal authentication redirect.
            if (error instanceof ApiError && error.status === 401) throw error
            clearDraftUrl()
            setDraftError(error instanceof ApiError && error.status === 404
              ? ERROR_CODES.draftNotFound : ERROR_CODES.draftLoadFailed)
          }
        }
      } catch (error) {
        if (!isActive) return
        if (error instanceof ApiError && error.status === 401) {
          router.replace('/login')
          return
        }

        console.error(
          JSON.stringify({
            event: 'store_initial_load_failed',
            message: error instanceof Error ? error.message : 'Unknown load error',
            status: error instanceof ApiError ? error.status : null,
          }),
        )

        if (isActive) {
          setProjectError(ERROR_CODES.workspaceLoadFailed)
        }
      } finally {
        if (isActive) setIsLoadingProjects(false)
      }
    }

    void loadInitialData()

    return () => {
      isActive = false
    }
  // Locale changes update UI copy without discarding the temporary document.
  }, [router, restoreDraft])

  function selectProject(id: string) {
    analysisRun.current += 1
    setSelectedProjectId(id)
    setRequestText('')
    setAnalyzedRequest(null)
    clearDocument()
    setCurrentHistoryEntryId(null)
    setAnalysisError('')
    setStatus('idle')
  }

  async function createProject(input: NewProjectInput) {
    const data = await apiFetch<ProjectResponse>('/api/projects', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(input),
    })

    analysisRun.current += 1
    setProjects((prev) => [data.project, ...prev])
    setSelectedProjectId(data.project.id)
    setRequestText('')
    setAnalyzedRequest(null)
    clearDocument()
    setCurrentHistoryEntryId(null)
    setAnalysisError('')
    setStatus('idle')
    setView('check')
    return data.project
  }

  async function updateProject(id: string, input: NewProjectInput) {
    const prior = projects.find((project) => project.id === id)
    const data = await apiFetch<ProjectResponse>(`/api/projects/${id}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
    })
    setProjects((prev) => prev.map((project) => project.id === id ? data.project : project))
    if (prior && projectAnalysisInputsChanged(prior, input)) {
      analysisRun.current += 1
      clearDocument()
      setAnalyzedRequest(null)
      setCurrentHistoryEntryId(null)
      setAnalysisError('')
      setStatus('idle')
    }
    setView('check')
    return data.project
  }

  async function createEstimate(projectId: string, request: string, documentLanguage?: string) {
    const run = analysisRun.current
    const project = analysisProject?.id === projectId ? analysisProject : projects.find((item) => item.id === projectId)
    const storedEndDate = draftDocument?.changeOrder?.endDate ?? draftDocument?.projectDetails.endDate ?? ''
    const endDate = validISODate(storedEndDate) && (!project?.startDate || storedEndDate >= project.startDate) ? storedEndDate : ''
    const data = await apiFetch<{ result: AnalysisResult }>('/api/change-orders/estimate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ projectId, request, locale: analysisLocale, ...(currentDraftId ? { draftId: currentDraftId } : draftProof ? { proof: draftProof } : {}), ...(endDate ? { endDate } : {}), ...(documentLanguage ? { documentLanguage } : {}) }),
    })
    if (run !== analysisRun.current) throw new Error('stale_estimate')
    if (!project) throw new Error('project_missing')
    setDraftDocument((current) => {
      if (!current) return current
      const updated: AnalysisResult = { ...current.result, changeOrder: data.result.changeOrder, draftCreatedAt: data.result.draftCreatedAt, commercialSignature: data.result.commercialSignature, estimateValid: data.result.estimateValid, changeOrderLabels: data.result.changeOrderLabels }
      const nextMaterials = current.clientMaterials ? { ...current.clientMaterials, changeOrder: { description: updated.changeOrder.description, timelineImpact: updated.changeOrder.timelineImpact, rationale: updated.changeOrder.rationale ?? '', note: updated.changeOrder.note }, changeOrderLabels: data.result.changeOrderLabels } : null
      const material = nextMaterials ? applyClientMaterials(updated, nextMaterials) : updated
      const proposed = editableChangeOrder(material, project, current.projectDetails, draftSessionId)
      return { ...current, result: updated, clientMaterials: nextMaterials, changeOrder: current.changeOrder ? mergeEstimate(current.changeOrder, proposed) : proposed }
    })
    return data.result
  }

  async function changeClientLanguage(language: string): Promise<boolean> {
    if (!user || !selectedProject || !analyzedRequest || !result) throw new Error('no_current_result')
    const run = analysisRun.current
    const original = result
    const data = await apiFetch<{ materials: ClientMaterials }>('/api/client-materials/language', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ projectId: selectedProject.id, locale: analysisLocale, ...(currentDraftId ? { draftId: currentDraftId } : draftProof ? { proof: draftProof } : {}), ...(currentHistoryEntryId ? { historyId: currentHistoryEntryId } : {}), request: analyzedRequest, clientLanguage: language, analysis: clientMaterials ? applyClientMaterials(original, clientMaterials) : original }),
    })
    if (run !== analysisRun.current) return true
    const materials = parseClientMaterials(data.materials, language)
    setDraftDocument((current) => {
      if (!current) return current
      const material = applyClientMaterials(current.result, materials)
      const proposed = editableChangeOrder(material, analysisProject ?? selectedProject, current.projectDetails, draftSessionId)
      return { ...current, clientMaterials: materials,
        reply: { tone: current.reply.tone, text: current.reply.text === current.reply.generated[current.reply.tone] ? materials.replies[current.reply.tone] : current.reply.text, generated: materials.replies },
        changeOrder: current.changeOrder ? mergeEstimate(current.changeOrder, proposed) : null }
    })
    return true
  }

  function loadExample(text: string) {
    analysisRun.current += 1
    setRequestText(text)
    setAnalyzedRequest(null)
    clearDocument()
    setCurrentHistoryEntryId(null)
    setAnalysisError('')
    setStatus('idle')
  }

  function applyHistory(projectId: string, entry: HistoryEntry) {
    setProjects((prev) =>
      prev.map((p) =>
        p.id === projectId
          ? {
              ...p,
              lastChecked: entry.date,
              history: [entry, ...p.history.filter((existing) => existing.id !== entry.id)],
            }
          : p,
      ),
    )
  }

  function clearDraftUrl() {
    if (typeof window === 'undefined') return
    const url = new URL(window.location.href)
    url.searchParams.delete('draft')
    window.history.replaceState(window.history.state, '', url)
  }
  function clearDocument() {
    setDraftDocument(null)
    setAnalysisSnapshot(null)
    setProjectSnapshot(null)
    setDraftProof(null)
    setCurrentDraftId(null)
    setDraftSessionId('')
    setSavedSignature('')
    setDraftError('')
    clearDraftUrl()
  }
  async function openDraft(id: string) {
    const openRun = ++draftOpenRun.current
    const run = ++analysisRun.current
    setDraftError('')
    try {
      const { draft } = await apiFetch<{ draft: SavedDraft }>(`/api/drafts/${id}`, { cache: 'no-store' })
      if (run === analysisRun.current && openRun === draftOpenRun.current) restoreDraft(draft)
    } catch (error) {
      if (run !== analysisRun.current || openRun !== draftOpenRun.current) return
      setDraftError(error instanceof ApiError ? error.message as ErrorCode : ERROR_CODES.draftLoadFailed)
      throw error
    }
  }
  function updateChangeOrder(draft: EditableDraft) {
    setDraftDocument((current) => current ? { ...current, changeOrder: draft } : current)
    setDraftError('')
  }
  function updateReply(reply: ReplyDocument) {
    setDraftDocument((current) => current ? { ...current, reply } : current)
    setDraftError('')
  }
  async function saveDraft() {
    if (!currentDraftId && !draftProof) { setDraftError(ERROR_CODES.draftProofInvalid); return }
    if (savingDraft.current || !draftDocument || !analysisSnapshot || !selectedProject || !analyzedRequest) return
    savingDraft.current = true
    setIsSavingDraft(true)
    setDraftError('')
    const run = analysisRun.current
    try {
      const response: { draft: SavedDraft; entry?: HistoryEntry } = currentDraftId
        ? await apiFetch<{ draft: SavedDraft }>(`/api/drafts/${currentDraftId}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ draftDocument }),
          })
        : await apiFetch<CreatedDraftResponse>('/api/drafts', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ projectId: selectedProject.id, request: analyzedRequest, locale: analysisLocale, idempotencyKey: draftSessionId, proof: draftProof, draftDocument }),
          })
      if (response.entry) applyHistory(response.draft.projectId, response.entry)
      if (run !== analysisRun.current) return
      setCurrentDraftId(response.draft.id)
      setCurrentHistoryEntryId(response.draft.historyEntryId)
      // Retain newer edits if a retried POST returns an already committed document.
      setSavedSignature(JSON.stringify(response.draft.draftDocument))
      const url = new URL(window.location.href)
      url.searchParams.set('draft', response.draft.id)
      window.history.replaceState(window.history.state, '', url)
    } catch (error) {
      if (run === analysisRun.current) setDraftError(error instanceof ApiError ? error.message as ErrorCode : ERROR_CODES.draftSaveFailed)
    } finally {
      savingDraft.current = false
      setIsSavingDraft(false)
    }
  }

  async function runAnalysis(project: Project, request: string) {
    const run = ++analysisRun.current
    try {
      const storedEndDate = user ? readProjectDetails(user.id, project.id).endDate : ''
      const endDate = validISODate(storedEndDate) && (!project.startDate || storedEndDate >= project.startDate) ? storedEndDate : ''
      const data = await apiFetch<{ result: AnalysisResult; proof: string; projectSnapshot: ProjectSnapshot }>(
        '/api/analyze',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ projectId: project.id, request, ...(endDate ? { endDate } : {}) }),
        },
      )

      const analysis = data.result
      if (run !== analysisRun.current) return
      const seed = crypto.randomUUID()
      const details = user ? readProjectDetails(user.id, project.id) : { clientName: '', clientEmail: '', endDate: '' }
      setCurrentHistoryEntryId(null)
      setCurrentDraftId(null)
      setAnalysisSnapshot(analysis)
      setDraftProof(data.proof)
      setProjectSnapshot(data.projectSnapshot)
      setAnalysisLocale(locale === 'ru' ? 'ru' : 'en')
      setDraftSessionId(seed)
      setSavedSignature('')
      setAnalyzedRequest(request)
      setDraftDocument({
        version: 1, result: analysis, clientMaterials: null,
        reply: { tone: 'neutral', text: analysis.replies.neutral, generated: analysis.replies },
        projectDetails: details,
        changeOrder: analysis.verdict !== 'in_scope' && (analysis.hasAdditionalWork ?? analysis.verdict === 'out_of_scope')
          ? editableChangeOrder(analysis, project, details, seed) : null,
      })
      setStatus('result')
    } catch (error) {
      if (run !== analysisRun.current) return
      console.error(
        JSON.stringify({
          event: 'scope_check_failed',
          projectId: project.id,
          message: error instanceof Error ? error.message : 'Unknown scope check error',
          status: error instanceof ApiError ? error.status : null,
        }),
      )
      if (error instanceof ApiError && error.status === 401) {
        router.replace('/login')
        return
      }
      setAnalysisError(
        error instanceof ApiError
          ? (error.message as ErrorCode)
          : ERROR_CODES.requestFailed,
      )
      setStatus('error')
    }
  }

  function runCheck() {
    const project = projects.find((p) => p.id === selectedProjectId)
    if (!project) return
    const scope = project.scope.trim()
    const request = requestText.trim()
    if (!request) return

    if (scope.length === 0) {
      setStatus('idle')
      return
    }
    if (scope.length < 60) {
      setStatus('short_scope')
      clearDocument()
      return
    }

    setStatus('loading')
    setAnalyzedRequest(null)
    clearDocument()
    setCurrentHistoryEntryId(null)
    setAnalysisError('')
    void runAnalysis(project, request)
  }

  function reset() {
    analysisRun.current += 1
    setAnalyzedRequest(null)
    clearDocument()
    setCurrentHistoryEntryId(null)
    setAnalysisError('')
    setStatus('idle')
  }

  async function logout() {
    await apiFetch<{ ok: true }>('/api/auth/logout', {
      method: 'POST',
    })
    router.replace('/login')
  }

  async function submitEvaluation(input: {
    accuracy: EvaluationAccuracy
    humanVerdict?: Verdict
  }) {
    if (!currentHistoryEntryId) {
      throw new Error('currentHistoryEntryId is required')
    }
    if (!result) {
      throw new Error('result is required')
    }
    if (input.accuracy === 'wrong' && !input.humanVerdict) {
      throw new Error('humanVerdict is required')
    }

    const body: Record<string, unknown> = {
      historyEntryId: currentHistoryEntryId,
      accuracy: input.accuracy,
      aiReasoning: result.reasoning,
    }
    if (input.accuracy === 'wrong') {
      body.humanVerdict = input.humanVerdict
    }

    try {
      await apiFetch<{ evaluation: { id: string } }>('/api/evaluations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'evaluation_submit_failed',
          message: error instanceof Error ? error.message : 'Unknown evaluation error',
          status: error instanceof ApiError ? error.status : null,
        }),
      )
      if (error instanceof ApiError && error.status === 401) {
        router.replace('/login')
      }
      throw error
    }
  }

  async function downloadEvaluationsExport() {
    let response: Response
    try {
      response = await fetch('/api/evaluations/export')
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'evaluation_export_request_failed',
          message: error instanceof Error ? error.message : 'Unknown export error',
        }),
      )
      throw new ApiError(ERROR_CODES.requestFailed, 0)
    }

    if (response.status === 401) {
      router.replace('/login')
      throw new ApiError(ERROR_CODES.authRequired, 401)
    }

    if (!response.ok) {
      console.error(
        JSON.stringify({
          event: 'evaluation_export_http_failed',
          status: response.status,
        }),
      )
      throw new ApiError(ERROR_CODES.requestFailed, response.status)
    }

    try {
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'scope-creep-evaluations.jsonl'
      link.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'evaluation_export_blob_failed',
          message: error instanceof Error ? error.message : 'Unknown blob error',
        }),
      )
      throw new ApiError(ERROR_CODES.requestFailed, response.status)
    }
  }

  const value: StoreValue = {
    user,
    projects,
    selectedProject,
    analysisProject, projectSnapshot,
    selectedProjectId,
    view,
    requestText,
    analyzedRequest,
    status,
    result,
    clientMaterials,
    draftDocument, currentDraftId, draftSessionId, isSavingDraft, draftError,
    isDraftDirty: !!currentDraftId && JSON.stringify(draftDocument) !== savedSignature,
    saveDraft, openDraft, listDrafts, updateChangeOrder, updateReply,
    changeClientLanguage,
    currentHistoryEntryId,
    analysisError,
    isLoadingProjects,
    projectError,
    setView,
    selectProject,
    createProject,
    updateProject,
    createEstimate,
    setRequestText,
    loadExample,
    runCheck,
    reset,
    logout,
    submitEvaluation,
    downloadEvaluationsExport,
  }

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useStore() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useStore must be used within StoreProvider')
  return ctx
}
