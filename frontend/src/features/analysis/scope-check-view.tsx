import { useTranslations } from 'use-intl'
import { useProjects } from '@/features/projects'
import { useWorkspaceNavigation } from '@/shared/ui/navigation'
import { Button } from '@/shared/ui/button'
import { RequestPanel } from './request-panel'
import { ResultPanel } from './result-panel'
import { DraftExportAction, LegacyStateView, useDrafts } from '@/features/drafts'

export function ScopeCheckView() {
  const { selectedProject } = useProjects()
  const { workflow, currentDraftId } = useDrafts()
  const { setView } = useWorkspaceNavigation()
  const t = useTranslations()
  if (workflow?.legacyRevision) return <LegacyStateView />
  return <div>
    <div className="screen-heading flex-wrap gap-3"><div><h1>{t('nav.check')}</h1></div>{selectedProject && <div className="ml-auto flex flex-wrap items-start gap-2"><DraftExportAction key={currentDraftId} /><Button variant="outline" onClick={() => setView('edit_project')}>{t('projects.editTitle')}</Button></div>}</div>
    {!selectedProject ? <RequestPanel /> : <div className="check-workbench"><RequestPanel /><div className="assessment-workspace"><ResultPanel /></div></div>}
  </div>
}
