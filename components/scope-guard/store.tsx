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
import { analyzeRequest, AnalysisError } from '@/lib/analyze'
import type {
  AnalysisResult,
  HistoryEntry,
  Industry,
  Project,
  Verdict,
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
  isLoadingProjects: boolean
  projectError: string

  setView: (v: View) => void
  selectProject: (id: string) => void
  createProject: (input: NewProjectInput) => Promise<void>
  setRequestText: (t: string) => void
  loadExample: (text: string, forceError: boolean) => void
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
    message: string,
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
  try {
    const body = await response.json()
    if (body && typeof body.error === 'string') return body.error
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'api_error_body_invalid',
        status: response.status,
        message: error instanceof Error ? error.message : 'Unknown JSON parse error',
      }),
    )
  }
  return 'The request failed.'
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
  const response = await fetch(input, init)

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
  const [isLoadingProjects, setIsLoadingProjects] = useState(true)
  const [projectError, setProjectError] = useState('')

  const forceErrorRef = useRef(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

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
          setProjectError('Unable to load your workspace. Please refresh the page.')
        }
      } finally {
        if (isActive) setIsLoadingProjects(false)
      }
    }

    void loadInitialData()

    return () => {
      isActive = false
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [router])

  function selectProject(id: string) {
    setSelectedProjectId(id)
    setRequestText('')
    setResult(null)
    setStatus('idle')
    forceErrorRef.current = false
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
    setStatus('idle')
    setView('check')
  }

  function loadExample(text: string, forceError: boolean) {
    setRequestText(text)
    forceErrorRef.current = forceError
    setResult(null)
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

  async function runAnalysis(project: Project, request: string, shouldError: boolean) {
    try {
      const analysis = analyzeRequest(project.scope, request, {
        forceError: shouldError,
      })

      const entry = {
        date: todayISO(),
        request,
        verdict: analysis.verdict as Verdict,
        summary: analysis.summary,
      }

      await persistHistory(project.id, entry)
      forceErrorRef.current = false
      setResult(analysis)
      setStatus('result')
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'scope_check_failed',
          projectId: project.id,
          isAnalysisError: error instanceof AnalysisError,
          message: error instanceof Error ? error.message : 'Unknown scope check error',
          status: error instanceof ApiError ? error.status : null,
        }),
      )

      if (error instanceof ApiError && error.status === 401) {
        router.replace('/login')
        return
      }

      forceErrorRef.current = false
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

    if (timerRef.current) clearTimeout(timerRef.current)
    setStatus('loading')
    setResult(null)

    const shouldError = forceErrorRef.current
    timerRef.current = setTimeout(() => {
      void runAnalysis(project, request, shouldError)
    }, 1500)
  }

  function reset() {
    setResult(null)
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
