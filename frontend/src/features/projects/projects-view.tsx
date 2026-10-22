import { OnboardingSlot } from '@/features/onboarding'
import { ArrowRight, Plus } from 'lucide-react'
import { useLocale, useTranslations } from 'use-intl'
import { Button } from '@/shared/ui/button'
import { localeToDateLocale, type Locale } from '@/shared/i18n/config'
import type { Industry, Project } from '@/shared/api/models'
import { DeleteProjectAction } from '@/features/projects/delete-project-action'
import { useProjects } from './resources'
import { useWorkspaceNavigation } from '@/shared/ui/navigation'

function formatDate(iso: string, locale: Locale) {
  const d = new Date(iso)
  return d.toLocaleDateString(localeToDateLocale(locale), {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function industryLabelKey(industry: Industry) {
  return `industry.${industry}` as const
}

function terms(project: Project, locale: string) {
  const amount = project.pricingModel === 'hourly' ? project.hourlyRate : project.fixedPrice
  if (amount == null || amount === '' || !Number.isFinite(Number(amount))) return '—'
  return new Intl.NumberFormat(locale, { style: project.currency ? 'currency' : 'decimal', currency: project.currency ?? undefined }).format(Number(amount))
}

export function ProjectsView() {
  const { projects, selectProject, setView } = { ...useProjects(), ...useWorkspaceNavigation() }
  const locale = useLocale()
  const t = useTranslations()

  return <section>
    <div className="screen-heading"><div><h1>{t('projects.title')}</h1></div>{projects.length > 0 && <Button type="button" data-onboarding="create-project" onClick={() => setView('new_project')}><Plus size={16} aria-hidden="true" />{t('projects.newProject')}</Button>}</div>
    {projects.length > 0 && <OnboardingSlot step={0} />}
    {projects.length === 0 ? <div className="collection-empty project-start"><h2>{t('projects.emptyTitle')}</h2><Button data-onboarding="create-project" onClick={() => setView('new_project')}><Plus size={16} aria-hidden="true" />{t('projects.createFirst')}<ArrowRight size={16} aria-hidden="true" /></Button><OnboardingSlot step={0} /></div> :
    <table className="project-table"><thead><tr><th>{t('projects.nameLabel')}</th><th className="project-terms">{t('design.projectTerms')}</th><th>{t('design.lastCheck')}</th><th><span className="sr-only">{t('design.projectActions')}</span></th></tr></thead><tbody>
      {projects.map(project => <tr key={project.id}>
        <td><button className="project-identity" onClick={() => selectProject(project.id)}>{project.name}</button><small>{project.clientName ? `${project.clientName} · ` : ''}{t(industryLabelKey(project.industry))}</small></td>
        <td className="project-terms">{terms(project, locale)}<small>{t(project.pricingModel === 'hourly' ? 'projects.hourly' : 'projects.fixed')}</small></td>
        <td className="text-sm">{project.lastChecked ? formatDate(project.lastChecked, locale) : t('projects.notCheckedYet')}</td>
        <td><div className="project-actions"><Button variant="ghost" onClick={() => selectProject(project.id, 'edit_project')}>{t('projects.edit')}</Button><DeleteProjectAction project={project} /></div></td>
      </tr>)}
    </tbody></table>}
  </section>
}
