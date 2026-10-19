import { ScopeCheckView } from '@/features/analysis'
import { ProjectsView, ArchivedProjects, NewProjectView, useProjects } from '@/features/projects'
import { MyDraftsView } from '@/features/drafts'
import { PersistentHistoryView } from '@/features/history'

export function CheckPage() { return <ScopeCheckView /> }
export function ProjectsPage() { return <><ProjectsView /><ArchivedProjects /></> }
export function NewProjectPage() { return <NewProjectView /> }
export function EditProjectPage() { const { selectedProjectId } = useProjects(); return <NewProjectView key={selectedProjectId} edit /> }
export function HistoryPage() { const { selectedProjectId } = useProjects(); return <PersistentHistoryView key={selectedProjectId} /> }
export function DraftsPage() { return <MyDraftsView /> }
