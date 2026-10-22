import { AgreementHost } from '@/features/change-orders'
import { useTranslations } from 'use-intl'
import { useProjects } from '@/features/projects'
import { useWorkspaceNavigation } from '@/shared/ui/navigation'
import { Button } from '@/shared/ui/button'
import { RequestPanel } from './request-panel'
import { ResultPanel } from './result-panel'
import { LegacyStateView, useDrafts } from '@/features/drafts'

export function ScopeCheckView() {
  const { selectedProject } = useProjects()
  const { workflow } = useDrafts()
  const { setView } = useWorkspaceNavigation()
  const t = useTranslations()
  if (workflow?.legacyRevision) return <LegacyStateView />
  return <AgreementHost><div>
    <div className="screen-heading"><div><h1>{t('nav.check')}</h1></div>{selectedProject && <Button variant="outline" onClick={() => setView('edit_project')}>{t('projects.editTitle')}</Button>}</div>
    {!selectedProject ? <RequestPanel /> : <div className="check-workbench"><RequestPanel /><div className="assessment-workspace"><ResultPanel /></div></div>}
  </div></AgreementHost>
}
