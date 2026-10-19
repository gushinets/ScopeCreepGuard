import { useRef } from 'react'
import { type DraftEditor, type WorkflowOperations, workflowApi, type WorkingDraft } from '@/features/drafts'
import { projectsApi, type NewProjectInput, type PersistentProject } from './api'
import type { useProjectResources } from './resources'
import type { ProjectDetails } from './model/browser-details'
import type { Project } from '@/shared/api/models'

export function useProjectActions(editor: DraftEditor, resources: ReturnType<typeof useProjectResources>, commands: WorkflowOperations,
  beforeTransition: () => Promise<void>, show: (view: 'check' | 'projects' | 'edit_project' | 'history', projectId?: string) => void) {
  const confirmed = useRef(new Map<string, PersistentProject>())
  async function select(id: string, destination: 'check' | 'edit_project' = 'check') {
    const run = ++editor.navigation.current
    await beforeTransition()
    const data = await workflowApi<{ draft: WorkingDraft }>(`projects/${encodeURIComponent(id)}/draft`)
    if (run !== editor.navigation.current) return
    editor.install(data.draft); show(destination, id)
  }
  async function createProject(input: NewProjectInput) {
    const run = ++editor.navigation.current
    await editor.beforeNavigate()
    const parameters = { ...input, clientEmail: input.clientEmail || null, endDate: input.endDate || null }
    const signature = JSON.stringify(['create', parameters])
    const project = confirmed.current.get(signature) ?? (await commands.run<{ project: PersistentProject }>('projects', parameters)).project
    confirmed.current.set(signature, project); resources.upsert(project)
    const saved = await workflowApi<{ draft: WorkingDraft }>(`projects/${project.id}/draft`)
    if (run === editor.navigation.current) { editor.install(saved.draft); show('check') }
    confirmed.current.delete(signature); return project
  }
  async function updateProject(id: string, input: NewProjectInput, details?: ProjectDetails) {
    const run = editor.navigation.current
    const saved = await editor.flush()
    const parameters = { ...input, clientName: details?.clientName ?? input.clientName, clientEmail: details?.clientEmail || null, endDate: details?.endDate || null, expectedRevision: saved.revision }
    const signature = JSON.stringify(['update', id, parameters])
    const updated = confirmed.current.get(signature) ?? (await commands.run<{ project: PersistentProject }>(`projects/${id}`, parameters, 'PATCH')).project
    confirmed.current.set(signature, updated); resources.upsert(updated)
    const refreshed = await workflowApi<{ draft: WorkingDraft }>(`projects/${id}/draft`)
    if (run === editor.navigation.current) { editor.install(refreshed.draft); show('check') }
    confirmed.current.delete(signature); return updated
  }
  async function deleteProject(id: string) {
    const run = ++editor.navigation.current
    const current = editor.controller.current
    await beforeTransition(); await projectsApi.remove(id)
    const remaining = resources.projects.filter(project => project.id !== id)
    resources.remove(id)
    if (run !== editor.navigation.current || current !== editor.controller.current) return
    if (current?.confirmed.projectId === id) {
      const replacement = remaining[0] ? (await workflowApi<{ draft: WorkingDraft }>(`projects/${remaining[0].id}/draft`)).draft : null
      if (run !== editor.navigation.current || current !== editor.controller.current) return
      editor.install(replacement)
    }
    show('projects')
  }
  async function openArchived(project: Project) {
    resources.upsert(project)
    await select(project.id); show('history')
  }
  function selectProject(id: string, destination?: 'check' | 'edit_project') {
    const selection = select(id, destination)
    const run = editor.navigation.current
    void selection.catch(failure => { if (run === editor.navigation.current) editor.report(failure) })
  }
  return { selectProject,
    select, createProject, updateProject, deleteProject, archivedProjects: async () => (await projectsApi.list(true)).projects, openArchived }
}
