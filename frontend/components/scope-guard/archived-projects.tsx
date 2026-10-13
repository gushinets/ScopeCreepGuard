'use client'
import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import type { Project } from '@/lib/types'
import { useStore } from './store'

export function ArchivedProjects() {
  const { workflow } = useStore()
  const t = useTranslations()
  const [projects, setProjects] = useState<Project[]>([])
  const [failed, setFailed] = useState(false)
  if (!workflow) return null
  return <section className="mx-auto mt-6 max-w-3xl"><Button variant="outline" onClick={() => { void workflow.archivedProjects().then(setProjects).catch(() => setFailed(true)) }}>{t('workflow.archivedProjects')}</Button>{failed && <p role="alert">{t('errors.requestFailed')}</p>}<ul className="mt-3 space-y-2">{projects.map(project => <li key={project.id}><Button variant="outline" onClick={() => { void workflow.openArchived(project).catch(() => setFailed(true)) }}>{project.name} · {t('history.title')}</Button></li>)}</ul></section>
}
