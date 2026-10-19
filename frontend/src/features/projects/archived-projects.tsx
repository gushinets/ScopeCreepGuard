import { useState } from 'react'
import { useTranslations } from 'use-intl'
import { Button } from '@/shared/ui/button'
import type { Project } from '@/shared/api/models'
import { useProjects } from './resources'

export function ArchivedProjects() {
  const { archivedProjects, openArchived } = { ...useProjects() }
  const t = useTranslations()
  const [projects, setProjects] = useState<Project[]>([])
  const [failed, setFailed] = useState(false)
  return <section className="mx-auto mt-6 max-w-3xl"><Button variant="outline" onClick={() => { void archivedProjects().then(setProjects).catch(() => setFailed(true)) }}>{t('workflow.archivedProjects')}</Button>{failed && <p role="alert">{t('errors.requestFailed')}</p>}<ul className="mt-3 space-y-2">{projects.map(project => <li key={project.id}><Button variant="outline" onClick={() => { void openArchived(project).catch(() => setFailed(true)) }}>{project.name} · {t('history.title')}</Button></li>)}</ul></section>
}
