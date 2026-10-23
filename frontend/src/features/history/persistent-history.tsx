import { ChevronDown, ChevronRight, RotateCcw } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslations } from 'use-intl'
import { Button } from '@/shared/ui/button'
import { workflowApi } from '@/features/drafts/contracts'
import type { Agreement, ArchivedCheck, DocumentExport } from '@/features/drafts/contracts'
import { AgreementPdfDownload, ChangeOrderDocumentPreview, downloadChangeOrder } from '@/features/change-orders'
import { useProjects, type PersistentProject } from '@/features/projects'
import { useHistory } from './operations'
import { ScopeAssessment } from '@/features/analysis'
import { ArchivedDraft } from './archived-draft'


function ExportItem({ initial }: { initial: DocumentExport }) {
  const t = useTranslations()
  const [item, setItem] = useState(initial)
  const [error, setError] = useState(false)
  const retryKey = useRef(crypto.randomUUID())
  useEffect(() => {
    if (!['pending', 'processing'].includes(item.status)) return
    let active = true
    const timer = setInterval(() => { void workflowApi<{ export: DocumentExport }>(`exports/${item.id}`).then(value => { if (active) { setItem(value.export); setError(false) } }).catch(() => { if (active) setError(true) }) }, 2000)
    return () => { active = false; clearInterval(timer) }
  }, [item.id, item.status])
  async function retry() {
    try { setItem((await workflowApi<{ export: DocumentExport }>(`exports/${item.id}/retry`, { operationId: retryKey.current })).export); retryKey.current = crypto.randomUUID(); setError(false) } catch { setError(true) }
  }
  async function download() {
    try {
      const response = await fetch(`/api/v2/exports/${item.id}/download`, { cache: 'no-store' })
      if (!response.ok) throw new Error('download failed')
      const url = URL.createObjectURL(await response.blob())
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = `change-order-${item.id}.pdf`; anchor.click()
      setTimeout(() => URL.revokeObjectURL(url), 10000)
      setError(false)
    } catch { setError(true) }
  }
  return <li className="rounded border p-3"><span role="status">{t(`workflow.export.${item.status}`)}</span>{item.status === 'ready' && <Button className="ml-3" variant="outline" onClick={() => void download()}>{t('workflow.download')}</Button>}{item.status === 'failed' && <Button className="ml-3" variant="outline" onClick={() => void retry()}>{t('workflow.retryExport')}</Button>}{error && <p role="alert">{t('errors.requestFailed')}</p>}</li>
}

function AgreementItem({ agreement, archived, refresh }: { agreement: Agreement; archived: boolean; refresh: () => Promise<void> }) {
  const t = useTranslations()
  const [exports, setExports] = useState<DocumentExport[]>([])
  const [error, setError] = useState(false)
  const [busy, setBusy] = useState(false)
  const operation = useRef({ export: crypto.randomUUID(), void: crypto.randomUUID() })
  useEffect(() => {
    let active = true
    void workflowApi<{ exports: DocumentExport[] }>(`change-orders/${agreement.id}/exports`).then(value => { if (active) setExports(value.exports) }).catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [agreement.id])
  async function action(kind: 'export' | 'void') {
    setBusy(true)
    try {
      if (kind === 'export') {
        const value = await workflowApi<{ export: DocumentExport }>(`change-orders/${agreement.id}/exports`, { operationId: operation.current.export })
        setExports(current => [value.export, ...current.filter(item => item.id !== value.export.id)])
      } else { await workflowApi(`change-orders/${agreement.id}/void`, { operationId: operation.current.void, expectedRevision: agreement.revision }); await refresh() }
      operation.current[kind] = crypto.randomUUID(); setError(false)
    } catch { setError(true) } finally { setBusy(false) }
  }
  return <section className="mt-4 rounded border p-4"><h3 className="font-medium">{agreement.reference}</h3><p>{t(`workflow.agreement.${agreement.status}`)}</p><p className="mb-3 text-sm">{t('workflow.notAcceptance')}</p><ChangeOrderDocumentPreview draft={agreement.contentSnapshot.document} /><div className="mt-3 flex flex-wrap gap-2"><Button disabled={busy || archived || agreement.status !== 'finalized'} onClick={() => void action('export')}>{t('workflow.exportPdf')}</Button><Button disabled={busy || agreement.status !== 'finalized'} variant="outline" onClick={() => void action('void')}>{t('workflow.void')}</Button></div>{error && <p role="alert" className="mt-2">{t('errors.requestFailed')}</p>}<ul className="mt-3 space-y-2">{exports.map(item => <ExportItem key={item.id} initial={item} />)}</ul></section>
}

export function HistoryProjectDetails({ projectId }: { projectId?: string | null } = {}) {
  const { selectedProject: activeProject, projects, archivedProjects } = useProjects()
  const [archived, setArchived] = useState<PersistentProject[]>([])
  const [archivesFailed, setArchivesFailed] = useState(false)
  const [archivesLoading, setArchivesLoading] = useState(true)
  const available = [...projects, ...archived]
  const selectedProject = available.find(project => project.id === (projectId ?? activeProject?.id)) ?? (projectId ? null : available[0] ?? null)
  const { openHistory } = useHistory()
  const loadArchives = useRef(archivedProjects)
  useEffect(() => {
    let active = true
    void loadArchives.current().then(value => { if (active) { setArchived(value); setArchivesFailed(false) } }).catch(() => { if (active) setArchivesFailed(true) }).finally(() => { if (active) setArchivesLoading(false) })
    return () => { active = false }
  }, [])
  const t = useTranslations()
  const [selectedRecord, setSelected] = useState<ArchivedCheck | null>(null)
  const selected = selectedRecord?.projectId === selectedProject?.id ? selectedRecord : null
  const [agreements, setAgreements] = useState<Agreement[]>([])
  const [error, setError] = useState(false)
  const [busy, setBusy] = useState(false)
  async function refresh(id = selected?.id) {
    if (id) setAgreements((await workflowApi<{ changeOrders: Agreement[] }>(`history/${id}/change-orders`)).changeOrders)
  }
  async function open(id: string) {
    setBusy(true)
    try {
      const [saved, documents] = await Promise.all([
        workflowApi<{ entry: ArchivedCheck }>(`history/${id}`),
        workflowApi<{ changeOrders: Agreement[] }>(`history/${id}/change-orders`),
      ])
      setSelected(saved.entry); setAgreements(documents.changeOrders); setError(false)
    } catch { setError(true) } finally { setBusy(false) }
  }
  if (projectId && !selectedProject && !archivesLoading && archivesFailed) return <p role="alert">{t('errors.requestFailed')}</p>
  return <section><div className="history-layout"><div>{selectedProject?.archivedAt && <div className="border-b border-border p-4"><Button variant="outline" onClick={() => { setSelected(null); setAgreements([]); setError(false) }}>{t('history.savedDraft')}</Button></div>}{!selectedProject ? <p>{t('history.selectProject')}</p> : selectedProject.history.length === 0 ? <p className="collection-empty">{t('design.historyEmpty')}</p> : <ul className="history-list">{selectedProject.history.map(entry => <li key={entry.id} data-selected={selected?.id === entry.id}><p>{entry.request}</p><p className="mt-1 text-sm">{entry.summary}</p><Button className="mt-2" variant="outline" disabled={busy} onClick={() => void open(entry.id)}>{t('workflow.viewCheck')}</Button></li>)}</ul>}</div><div>{error && <p role="alert">{t('errors.requestFailed')}</p>}{!selected && selectedProject?.archivedAt && <ArchivedDraft key={selectedProject.id} project={selectedProject} />}{selected && <article className="history-detail"><h2>{selected.summary}</h2>{selected.sourceKind === 'legacy_unverified' ? <p className="mt-3">{t('workflow.legacyHistory')}</p> : <>{openHistory && <Button className="mt-3" disabled={busy || !!selectedProject?.archivedAt || selectedProject?.id !== activeProject?.id} variant="outline" onClick={() => { setBusy(true); void openHistory(selected.id).catch(() => setError(true)).finally(() => setBusy(false)) }}>{t('workflow.reopen')}</Button>}<div className="mt-4">{selected.checkSnapshot.analysis ? <ScopeAssessment result={selected.checkSnapshot.analysis} request={selected.checkSnapshot.requestText} /> : <p className="whitespace-pre-wrap">{selected.checkSnapshot.requestText}</p>}</div><h4 className="mt-4 font-medium">{t('workflow.archivedScope')}</h4><p className="whitespace-pre-wrap">{selected.checkSnapshot.projectSnapshot?.scope}</p><h4 className="mt-4 font-medium">{t('reply.heading')}</h4><p className="whitespace-pre-wrap">{selected.checkSnapshot.draftDocument?.reply.text}</p>{selected.checkSnapshot.draftDocument?.changeOrder && <div className="mt-4"><ChangeOrderDocumentPreview draft={selected.checkSnapshot.draftDocument.changeOrder} /><div className="mt-3 flex flex-wrap gap-2"><AgreementPdfDownload language={selected.checkSnapshot.draftDocument.changeOrder.language} download={signal => downloadChangeOrder({ draft: selected.checkSnapshot.draftDocument!.changeOrder!, projectId: selected.projectId, persistentWorkflow: true }, signal)} /></div></div>}</>}{agreements.map(agreement => <AgreementItem key={`${agreement.id}:${agreement.revision}`} agreement={agreement} archived={!!selectedProject?.archivedAt} refresh={() => refresh()} />)}</article>}</div></div></section>
}


export function PersistentHistoryView({ projectId, onProjectChange }: { projectId?: string | null; onProjectChange?: (id: string) => void } = {}) {
  const t = useTranslations()
  const { projects, archivedProjects, restoreProject } = useProjects()
  const [archived, setArchived] = useState<PersistentProject[]>([])
  const [expanded, setExpanded] = useState<string | null>(projectId ?? null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [restoring, setRestoring] = useState<string | null>(null)
  const [restoreFailed, setRestoreFailed] = useState<string | null>(null)
  const load = useRef(archivedProjects)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    void load.current().then(value => { if (active) { setArchived(value); setFailed(false) } }).catch(() => { if (active) setFailed(true) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [attempt])
  async function restore(id: string) {
    setRestoring(id); setRestoreFailed(null)
    try { await restoreProject(id); setArchived(current => current.filter(project => project.id !== id)) }
    catch { setRestoreFailed(id) }
    finally { setRestoring(null) }
  }
  const available = [...projects, ...archived.filter(project => !projects.some(active => active.id === project.id))]
  return <section><div className="screen-heading"><div><h1>{t('history.title')}</h1></div></div>
    {loading && <p role="status">{t('history.loadingProjects')}</p>}
    {failed && <p role="alert">{t('history.archivesFailed')} <Button variant="ghost" onClick={() => { setLoading(true); setAttempt(value => value + 1) }}>{t('result.tryAgain')}</Button></p>}
    {!loading && !available.length && <p className="collection-empty">{t('design.historyEmpty')}</p>}
    <ul className="history-projects">{available.map(project => <li key={project.id} className="border-b border-border">
      <div className="flex items-center gap-3 py-3">
        <button type="button" aria-expanded={expanded === project.id} aria-controls={`history-details-${project.id}`} onClick={() => { setExpanded(current => current === project.id ? null : project.id); onProjectChange?.(project.id) }} className="flex min-w-0 flex-1 items-center gap-3 rounded-md px-2 py-2 text-left hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring">
          {expanded === project.id ? <ChevronDown aria-hidden="true" className="size-4 shrink-0" /> : <ChevronRight aria-hidden="true" className="size-4 shrink-0" />}
          <span className="min-w-0 flex-1"><span className="block truncate font-medium">{project.name}</span><span className="mt-1 line-clamp-1 text-sm text-muted-foreground">{project.clientName ? `${project.clientName} · ` : ''}{project.scope}</span></span>
          {project.archivedAt && <span className="ml-auto hidden shrink-0 text-xs text-muted-foreground sm:block">{t('history.archived')}</span>}
        </button>
        {project.archivedAt && <Button variant="outline" disabled={restoring !== null} onClick={() => void restore(project.id)}><RotateCcw aria-hidden="true" />{t(restoring === project.id ? 'history.restoring' : 'history.restoreProject')}</Button>}
      </div>
      {restoreFailed === project.id && <p role="alert" className="pb-3 text-sm text-outscope-text">{t('history.restoreFailed')}</p>}
      {expanded === project.id && <div id={`history-details-${project.id}`} className="pb-6"><h2 className="mb-2 text-base font-semibold">{t('history.projectOverview')}</h2><p className="mb-5 whitespace-pre-wrap text-sm">{project.scope}</p><HistoryProjectDetails key={`${project.id}:${project.archivedAt ?? 'active'}`} projectId={project.id} /></div>}
    </li>)}</ul>
  </section>
}
