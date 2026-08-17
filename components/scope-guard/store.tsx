'use client'

import { useRouter } from 'next/navigation'
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { ERROR_CODES, assertErrorCode, type ErrorCode } from '@/lib/api/errors'
import type {
  AnalysisResult,
  HistoryEntry,
  Industry,
  Project,
} from '@/lib/types'

export type View = 'check' | 'projects' | 'new_project' | 'history'

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
  client: string
  industry: Industry
  scope: string
}

interface StoreValue {
  user: AuthUser | null
  projects: Project[]
  selectedProject: Project | null
  selectedProjectId: string | null
  view: View
  requestText: string
  status: AnalysisStatus
  result: AnalysisResult | null
  analysisError: ErrorCode | ''
  isLoadingProjects: boolean
  projectError: ErrorCode | ''

  setView: (v: View) => void
  selectProject: (id: string) => void
  createProject: (input: NewProjectInput) => Promise<void>
  setRequestText: (t: string) => void
  loadExample: (text: string) => void
  runCheck: () => void
  reset: () => void
  logout: () => Promise<void>
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
  const [status, setStatus] = useState<AnalysisStatus>('idle')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [analysisError, setAnalysisError] = useState<ErrorCode | ''>('')
  const [isLoadingProjects, setIsLoadingProjects] = useState(true)
  const [projectError, setProjectError] = useState<ErrorCode | ''>('')

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
    setSelectedProjectId(id)
    setRequestText('')
    setResult(null)
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

    setProjects((prev) => [data.project, ...prev])
    setSelectedProjectId(data.project.id)
    setRequestText('')
    setResult(null)
    setAnalysisError('')
    setStatus('idle')
    setView('check')
  }

  function loadExample(text: string) {
    setRequestText(text)
    setResult(null)
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
  }

  async function runAnalysis(project: Project, request: string) {
    try {
      const data = await apiFetch<{ result: AnalysisResult }>(
        '/api/analyze',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ projectId: project.id, request }),
        },
      )

      const analysis = data.result
      await persistHistory(project.id, {
        date: todayISO(),
        request,
        verdict: analysis.verdict,
        summary: analysis.summary,
      })
      setResult(analysis)
      setStatus('result')
    } catch (error) {
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
    setResult(null)
    setAnalysisError('')
    void runAnalysis(project, request)
  }

  function reset() {
    setResult(null)
    setAnalysisError('')
    setStatus('idle')
  }

  async function logout() {
    await apiFetch<{ ok: true }>('/api/auth/logout', {
      method: 'POST',
    })
    router.replace('/login')
  }

  const value: StoreValue = {
    user,
    projects,
    selectedProject,
    selectedProjectId,
    view,
    requestText,
    status,
    result,
    analysisError,
    isLoadingProjects,
    projectError,
    setView,
    selectProject,
    createProject,
    setRequestText,
    loadExample,
    runCheck,
    reset,
    logout,
  }

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useStore() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useStore must be used within StoreProvider')
  return ctx
}
