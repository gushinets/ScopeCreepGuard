import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { useBlocker, useLocation, useNavigate } from 'react-router'
import { useSession } from '@/features/auth'
import { ProjectsContext, useProjectResources, useProjectActions, type ProjectsValue } from '@/features/projects'
import { DraftsContext, useDraftEditor, WorkflowOperations, workflowApi, readDraftLink, draftErrorCode, type WorkingDraft, type DraftsValue } from '@/features/drafts'
import { AnalysisContext, useAnalysisOperations, type AnalysisValue } from '@/features/analysis'
import { AgreementContext, useAgreementCommands } from '@/features/change-orders'
import { HistoryContext, useHistoryCommands } from '@/features/history'
import { NavigationContext } from '@/shared/ui/navigation'
import { pageView, workspacePath, type View } from '@/shared/config/navigation'
import type { DraftDocument, DraftListItem } from '@/features/drafts/contracts'
import type { AnalysisResult } from '@/shared/api/models'
import type { ErrorCode } from '@/shared/api/errors'

/** Composition only: feature hooks own resources, editor algorithms and operations. */
export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const { user } = useSession()
  if (!user) throw new Error('Authenticated workspace requires an owner')
  const navigate = useNavigate()
  const location = useLocation()
  const internal = useRef(false)
  const formGuard = useRef<(() => boolean) | null>(null)
  const locationRef = useRef(location)
  locationRef.current = location
  const syncDraftUrl = useCallback((id: string | null) => {
    const current = locationRef.current
    const query = new URLSearchParams(current.search)
    if (id) query.set('draft', id); else query.delete('draft')
    const search = query.size ? `?${query}` : ''
    if (search === current.search) return
    const next = { ...current, search }
    locationRef.current = next
    internal.current = true
    void navigate(next.pathname + next.search + next.hash, { replace: true, state: current.state })
    internal.current = false
  }, [navigate])
  const editor = useDraftEditor(user.id, syncDraftUrl)
  const resources = useProjectResources()
  const commands = useRef(new WorkflowOperations((path, body, method) => workflowApi(path, body, method), user.id)).current
  const analysis = useAnalysisOperations(editor, commands, resources.reload)
  function show(view: View, projectId = editor.controller.current?.confirmed.projectId) {
    const current = locationRef.current
    internal.current = true
    void navigate(workspacePath(view, current.search, current.hash, projectId), { state: current.state })
    internal.current = false
  }
  async function beforeTransition() {
    if (formGuard.current && !formGuard.current()) throw new Error('Navigation cancelled')
    await editor.beforeNavigate()
  }
  const projects = useProjectActions(editor, resources, commands, beforeTransition, show)
  const history = useHistoryCommands(editor, commands, entry => {
    resources.setProjects(current => current.map(project => project.id === entry.projectId ? { ...project, history: [entry, ...project.history.filter(item => item.id !== entry.id)] } : project))
  }, () => show('check'))
  const agreements = useAgreementCommands(editor, commands)
  const [loading, setLoading] = useState(true)
  const [projectError, setProjectError] = useState<ErrorCode | ''>('')
  const blocker = useBlocker(() => !internal.current && (!!formGuard.current || !!editor.controller.current && editor.controller.current.status !== 'saved'))
  const resolving = useRef(false)
  useEffect(() => {
    if (blocker.state !== 'blocked' || resolving.current) return
    resolving.current = true
    void beforeTransition().then(() => blocker.proceed()).catch(failure => { editor.report(failure); blocker.reset() }).finally(() => { resolving.current = false })
  })

  const initial = useRef({ editor, location })
  useEffect(() => {
    let active = true
    const start = initial.current
    async function initialize() {
      try {
        const loaded = await resources.reload()
        if (!active) return
        const id = new URLSearchParams(start.location.search).get('draft')
        const editProject = /^\/projects\/([^/]+)\/edit$/.exec(start.location.pathname)?.[1]
        if (editProject) {
          const data = await workflowApi<{ draft: WorkingDraft }>(`projects/${encodeURIComponent(decodeURIComponent(editProject))}/draft`)
          if (active) start.editor.install(data.draft)
        } else if (id) {
          const linked = await readDraftLink(id)
          if (!active) return
          if (linked) {
            start.editor.install(linked.draft, linked.legacy ? id : undefined)
            start.editor.setLegacyRevision(linked.legacy)
          } else {
            const fallback = loaded[0] ? (await workflowApi<{ draft: WorkingDraft }>(`projects/${loaded[0].id}/draft`)).draft : null
            if (active) start.editor.install(fallback)
          }
        } else if (loaded[0]) {
          const data = await workflowApi<{ draft: WorkingDraft }>(`projects/${loaded[0].id}/draft`)
          if (active) start.editor.install(data.draft)
        } else start.editor.install(null)
        const current = start.editor.controller.current
        if (active && current) {
          const resumed = await commands.resume(`drafts/${current.confirmed.id}/`)
          if (active && start.editor.controller.current === current && resumed.length) {
            const refreshed = await workflowApi<{ draft: WorkingDraft }>(`drafts/${current.confirmed.id}`)
            if (active && start.editor.controller.current === current && current.status === 'saved') start.editor.install(refreshed.draft)
          }
        }
      } catch (failure) { if (active) setProjectError(draftErrorCode(failure)) }
      finally { if (active) setLoading(false) }
    }
    void initialize()
    return () => { active = false }
  }, [resources.reload, commands])

  // POP navigation and direct URL changes activate the requested resource only after the save barrier.
  useEffect(() => {
    if (loading) return
    const id = new URLSearchParams(location.search).get('draft')
    const editProject = /^\/projects\/([^/]+)\/edit$/.exec(location.pathname)?.[1]
    const current = editor.controller.current
    if (editProject && decodeURIComponent(editProject) !== current?.confirmed.projectId) {
      void projects.select(decodeURIComponent(editProject), 'edit_project').catch(editor.report)
    } else if (id && id !== current?.confirmed.id && id !== editor.legacyRevision?.id) {
      void activateDraft(id, false).catch(editor.report)
    }
  }, [location.key, loading])

  async function activateDraft(id: string, navigateToCheck = true) {
    const run = ++editor.navigation.current
    await beforeTransition()
    try {
      const linked = await readDraftLink(id)
      if (run !== editor.navigation.current) return
      if (!linked) { syncDraftUrl(editor.controller.current?.confirmed.id ?? null); return }
      const { draft, legacy } = linked
      editor.install(draft, legacy ? id : undefined); editor.setLegacyRevision(legacy); analysis.resetStatus()
      if (navigateToCheck) show('check')
    } catch (failure) { editor.report(failure); throw failure }
  }
  const listDrafts = useCallback(async (): Promise<DraftListItem[]> => {
    const current = await workflowApi<{ projects: ProjectsValue['projects'] }>('projects')
    return Promise.all(current.projects.map(async project => {
      const { draft } = await workflowApi<{ draft: WorkingDraft }>(`projects/${project.id}/draft`)
      return { id: draft.id, projectName: project.name, requestPreview: draft.requestText.slice(0, 160), verdict: draft.analysisRun?.resultSnapshot?.verdict ?? null, createdAt: draft.createdAt, updatedAt: draft.updatedAt }
    }))
  }, [])
  const snapshot = editor.snapshot
  const selectedProject = resources.projects.find(project => project.id === snapshot?.projectId) ?? null
  const rawResult = snapshot?.analysisRun?.resultSnapshot
  const result: AnalysisResult | null = rawResult && snapshot ? { ...rawResult, replies: snapshot.draftDocument.reply.generated,
    clientLanguage: snapshot.draftDocument.reply.language, commercialSignature: snapshot.draftDocument.estimate?.commercialSignature ?? rawResult.commercialSignature,
    estimateValid: snapshot.draftDocument.estimate?.estimateValid ?? rawResult.estimateValid } : null
  const draftDocument: DraftDocument | null = snapshot && result ? { version: 1, result, clientMaterials: null,
    changeOrder: snapshot.draftDocument.changeOrder, reply: snapshot.draftDocument.reply, languageSelection: snapshot.draftDocument.languageSelection,
    projectDetails: { clientName: selectedProject?.clientName ?? '', clientEmail: selectedProject?.clientEmail ?? '', endDate: selectedProject?.endDate ?? '' } } : null
  const draftsValue: DraftsValue = { draftDocument, currentDraftId: snapshot?.id ?? null, draftSessionId: snapshot?.id ?? '',
    draftError: editor.draftError, isSavingDraft: editor.saveStatus === 'saving', isDraftDirty: editor.saveStatus !== 'saved',
    requestText: snapshot?.requestText ?? '', setRequestText: editor.setRequestText, loadExample: editor.setRequestText,
    updateReply: editor.updateReply, updateChangeOrder: editor.updateChangeOrder, saveDraft: editor.flush, openDraft: activateDraft, listDrafts,
    workflow: { status: editor.saveStatus, stale: snapshot?.analysisIsStale ?? true, recovery: editor.recovery,
      acceptRecovery: editor.acceptRecovery, discardRecovery: editor.discardRecovery, retrySave: editor.flush,
      compareConflict: editor.compareConflict, resolveConflict: editor.resolveConflict,
      legacyRevision: editor.legacyRevision, closeLegacy: editor.closeLegacy, archived: !!selectedProject?.archivedAt } }
  const analysisValue: AnalysisValue = { ...analysis, status: analysis.phase ?? (result ? 'result' : 'idle'), result,
    analysisProject: selectedProject && snapshot?.analysisRun ? { ...selectedProject, ...snapshot.analysisRun.projectSnapshot, id: selectedProject.id, history: selectedProject.history } : selectedProject,
    analyzedRequest: snapshot?.analysisRun?.requestText ?? null, termsChanged: !!snapshot?.analysisIsStale && !!result, currentHistoryEntryId: editor.historyId }
  return <NavigationContext.Provider value={{ view: pageView(location.pathname), setView: view => { const current = locationRef.current; void navigate(workspacePath(view, current.search, current.hash, snapshot?.projectId), { state: current.state }) }, beforeLeave: beforeTransition, registerForm: guard => { formGuard.current = guard } }}>
    <ProjectsContext.Provider value={{ projects: resources.projects, selectedProject, selectedProjectId: snapshot?.projectId ?? null, isLoadingProjects: loading, projectError, ...projects }}>
      <DraftsContext.Provider value={draftsValue}><AnalysisContext.Provider value={analysisValue}>
        <AgreementContext.Provider value={agreements}><HistoryContext.Provider value={history}>{children}</HistoryContext.Provider></AgreementContext.Provider>
      </AnalysisContext.Provider></DraftsContext.Provider>
    </ProjectsContext.Provider>
  </NavigationContext.Provider>
}
