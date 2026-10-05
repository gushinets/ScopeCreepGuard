'use client'

import { useRouter } from 'next/navigation'
import {
  createContext,
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

export type View = 'check' | 'projects' | 'new_project' | 'edit_project' | 'history'

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
  selectedProjectId: string | null
  view: View
  requestText: string
  analyzedRequest: string | null
  status: AnalysisStatus
  result: AnalysisResult | null
  currentHistoryEntryId: string | null
  analysisError: ErrorCode | ''
  isLoadingProjects: boolean
  projectError: ErrorCode | ''

  setView: (v: View) => void
  selectProject: (id: string) => void
  createProject: (input: NewProjectInput) => Promise<Project>
  updateProject: (id: string, input: NewProjectInput) => Promise<Project>
  createEstimate: (projectId: string, request: string, documentLanguage?: 'ru' | 'en') => Promise<AnalysisResult>
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

interface HistoryResponse {
  entry: HistoryEntry
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

function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

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

export function StoreProvider({ children }: { children: ReactNode }) {
  const router = useRouter()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [view, setView] = useState<View>('check')
  const [requestText, setRequestText] = useState('')
  const [analyzedRequest, setAnalyzedRequest] = useState<string | null>(null)
  const [status, setStatus] = useState<AnalysisStatus>('idle')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [currentHistoryEntryId, setCurrentHistoryEntryId] = useState<string | null>(
    null,
  )
  const [analysisError, setAnalysisError] = useState<ErrorCode | ''>('')
  const [isLoadingProjects, setIsLoadingProjects] = useState(true)
  const [projectError, setProjectError] = useState<ErrorCode | ''>('')
  const analysisRun = useRef(0)

  const selectedProject =
    projects.find((p) => p.id === selectedProjectId) ?? null

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
      } catch (error) {
        console.error(
          JSON.stringify({
            event: 'store_initial_load_failed',
            message: error instanceof Error ? error.message : 'Unknown load error',
            status: error instanceof ApiError ? error.status : null,
          }),
        )

        if (error instanceof ApiError && error.status === 401) {
          router.replace('/login')
          return
        }

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
  }, [router])

  function selectProject(id: string) {
    analysisRun.current += 1
    setSelectedProjectId(id)
    setRequestText('')
    setAnalyzedRequest(null)
    setResult(null)
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
    setResult(null)
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
      setResult(null)
      setAnalyzedRequest(null)
      setCurrentHistoryEntryId(null)
      setAnalysisError('')
      setStatus('idle')
    }
    setView('check')
    return data.project
  }

  async function createEstimate(projectId: string, request: string, documentLanguage?: 'ru' | 'en') {
    const storedEndDate = user ? readProjectDetails(user.id, projectId).endDate : ''
    const project = projects.find((item) => item.id === projectId)
    const endDate = validISODate(storedEndDate) && (!project?.startDate || storedEndDate >= project.startDate) ? storedEndDate : ''
    const data = await apiFetch<{ result: AnalysisResult }>('/api/change-orders/estimate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ projectId, request, ...(endDate ? { endDate } : {}), ...(documentLanguage ? { documentLanguage } : {}) }),
    })
    return data.result
  }

  function loadExample(text: string) {
    analysisRun.current += 1
    setRequestText(text)
    setAnalyzedRequest(null)
    setResult(null)
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
              history: [entry, ...p.history],
            }
          : p,
      ),
    )
  }

  async function persistHistory(projectId: string, entry: Omit<HistoryEntry, 'id'>) {
    const data = await apiFetch<HistoryResponse>(
      `/api/projects/${projectId}/history`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(entry),
      },
    )

    applyHistory(projectId, data.entry)
    return data.entry
  }

  async function runAnalysis(project: Project, request: string) {
    const run = ++analysisRun.current
    try {
      const storedEndDate = user ? readProjectDetails(user.id, project.id).endDate : ''
      const endDate = validISODate(storedEndDate) && (!project.startDate || storedEndDate >= project.startDate) ? storedEndDate : ''
      const data = await apiFetch<{ result: AnalysisResult }>(
        '/api/analyze',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ projectId: project.id, request, ...(endDate ? { endDate } : {}) }),
        },
      )

      const analysis = data.result
      if (run !== analysisRun.current) return
      const historyEntry = await persistHistory(project.id, {
        date: todayISO(),
        request,
        verdict: analysis.verdict,
        summary: analysis.summary,
      })
      if (run !== analysisRun.current) return
      setCurrentHistoryEntryId(historyEntry.id)
      setAnalyzedRequest(request)
      setResult(analysis)
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
      setResult(null)
      return
    }

    setStatus('loading')
    setAnalyzedRequest(null)
    setResult(null)
    setCurrentHistoryEntryId(null)
    setAnalysisError('')
    void runAnalysis(project, request)
  }

  function reset() {
    analysisRun.current += 1
    setAnalyzedRequest(null)
    setResult(null)
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
    selectedProjectId,
    view,
    requestText,
    analyzedRequest,
    status,
    result,
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
