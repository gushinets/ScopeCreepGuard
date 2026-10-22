import { ScopeCheckView } from '@/features/analysis'
import { useSearchParams } from 'react-router'
import { ProjectsView, NewProjectView, useProjects } from '@/features/projects'
import { MyDraftsView } from '@/features/drafts'
import { PersistentHistoryView } from '@/features/history'

export function CheckPage() { return <ScopeCheckView /> }
export function ProjectsPage() { return <ProjectsView /> }
export function NewProjectPage() { return <NewProjectView /> }
export function EditProjectPage() { const { selectedProjectId } = useProjects(); return <NewProjectView key={selectedProjectId} edit /> }
export function HistoryPage() {
  const [query, setQuery] = useSearchParams()
  return <PersistentHistoryView projectId={query.get('historyProject')} onProjectChange={id => { const next = new URLSearchParams(query); next.set('historyProject', id); setQuery(next, { replace: true }) }} />
}
export function DraftsPage() { return <MyDraftsView /> }
