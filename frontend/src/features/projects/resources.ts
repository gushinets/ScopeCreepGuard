import { useCallback, useRef, useState, type Dispatch, type SetStateAction } from 'react'
import { projectsApi, type PersistentProject, type NewProjectInput } from './api'
import { featureContext } from '@/shared/ui/feature-context'
import type { ProjectDetails } from './model/browser-details'
import type { Project } from '@/shared/api/models'

export function useProjectResources() {
  const [projects, updateProjects] = useState<PersistentProject[]>([])
  const version = useRef(0)
  const setProjects: Dispatch<SetStateAction<PersistentProject[]>> = useCallback(value => { version.current++; updateProjects(value) }, [])
  const reload = useCallback(async () => {
    const request = ++version.current
    const data = await projectsApi.list()
    if (request === version.current) updateProjects(data.projects)
    return data.projects
  }, [])
  const upsert = (project: PersistentProject) => setProjects(current => [project, ...current.filter(item => item.id !== project.id)])
  const remove = (id: string) => setProjects(current => current.filter(item => item.id !== id))
  return { projects, setProjects, reload, upsert, remove }
}

export interface ProjectsValue {
  projects: PersistentProject[]; selectedProject: PersistentProject | null; selectedProjectId: string | null
  isLoadingProjects: boolean; projectError: string
  selectProject: (id: string, destination?: 'check' | 'edit_project') => void
  createProject: (input: NewProjectInput) => Promise<Project>
  updateProject: (id: string, input: NewProjectInput, details?: ProjectDetails) => Promise<Project>
  deleteProject: (id: string) => Promise<void>
  restoreProject: (id: string) => Promise<void>
  archivedProjects: () => Promise<PersistentProject[]>
  openArchived: (project: Project) => Promise<void>
}
export const [ProjectsContext, useProjects] = featureContext<ProjectsValue>('Projects')
