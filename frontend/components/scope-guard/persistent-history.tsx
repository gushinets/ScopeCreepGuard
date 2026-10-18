'use client'

import { useEffect, useRef, useState } from 'react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { workflowApi, WorkflowApiError } from '@/lib/drafts/workflow-client'
import type { Agreement, ArchivedCheck, DocumentExport } from '@/lib/drafts/workflow-types'
import { ChangeOrderDocumentPreview } from './change-order-document-preview'
import { useStore } from './store'
import { ScopeAssessment } from './scope-assessment'

const readinessLabels = { description: 'changeOrder.descriptionLabel', estimatedHours: 'changeOrder.hoursLabel', additionalCost: 'changeOrder.costLabel', currency: 'changeOrder.currencyLabel' } as const

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
  return <section className="mt-4 rounded border p-4"><h3 className="font-medium">{agreement.reference}</h3><p>{t(`workflow.agreement.${agreement.status}`)}</p><p className="mb-3 text-sm">{t('workflow.notAcceptance')}</p><ChangeOrderDocumentPreview draft={agreement.contentSnapshot.document} /><div className="mt-3 flex gap-2"><Button disabled={busy || archived || agreement.status !== 'finalized'} onClick={() => void action('export')}>{t('workflow.exportPdf')}</Button><Button disabled={busy || agreement.status !== 'finalized'} variant="outline" onClick={() => void action('void')}>{t('workflow.void')}</Button></div>{error && <p role="alert" className="mt-2">{t('errors.requestFailed')}</p>}<ul className="mt-3 space-y-2">{exports.map(item => <ExportItem key={item.id} initial={item} />)}</ul></section>
}

export function PersistentHistoryView() {
  const { selectedProject, workflow, draftDocument } = useStore()
  const t = useTranslations()
  const [selected, setSelected] = useState<ArchivedCheck | null>(null)
  const [agreements, setAgreements] = useState<Agreement[]>([])
  const [error, setError] = useState(false)
  const [busy, setBusy] = useState(false)
  const finalizeKey = useRef(crypto.randomUUID())
  const [finalizeFields, setFinalizeFields] = useState<Record<string, string>>({})
  async function refresh(id = selected?.id) {
    if (id) setAgreements((await workflowApi<{ changeOrders: Agreement[] }>(`history/${id}/change-orders`)).changeOrders)
  }
  async function open(id: string) {
    setFinalizeFields({})
    setBusy(true)
    try { setSelected((await workflowApi<{ entry: ArchivedCheck }>(`history/${id}`)).entry); await refresh(id); setError(false); finalizeKey.current = crypto.randomUUID() } catch { setError(true) } finally { setBusy(false) }
  }
  async function finalize() {
    if (!selected) return
    setBusy(true)
    setFinalizeFields({})
    try { await workflowApi(`history/${selected.id}/change-orders`, { operationId: finalizeKey.current }); await refresh(); finalizeKey.current = crypto.randomUUID(); setError(false) } catch (failure) { setError(true); if (failure instanceof WorkflowApiError) setFinalizeFields(failure.fields ?? {}) } finally { setBusy(false) }
  }
  async function archiveEdits() {
    if (!workflow) return
    setBusy(true)
    try {
      await workflow.complete()
      setSelected(null); setAgreements([]); setFinalizeFields({}); setError(false)
    } catch { setError(true) } finally { setBusy(false) }
  }
  return <section className="mx-auto max-w-3xl"><h2 className="text-xl font-semibold">{t('history.title')}</h2><p className="mt-2 text-sm">{t('workflow.historyHelp')}</p>{workflow && draftDocument?.changeOrder && !workflow.legacyRevision && <div className="mt-3"><p className="text-sm text-muted-foreground">{t('workflow.archiveEditsHelp')}</p><Button className="mt-2" variant="outline" disabled={busy || workflow.archived} onClick={() => void archiveEdits()}>{t('workflow.archiveEdits')}</Button></div>}{!selectedProject ? <p>{t('history.selectProject')}</p> : <ul className="mt-4 space-y-3">{selectedProject.history.map(entry => <li key={entry.id} className="rounded border p-3"><p>{entry.request}</p><p className="mt-1 text-sm">{entry.summary}</p><Button className="mt-2" variant="outline" disabled={busy} onClick={() => void open(entry.id)}>{t('workflow.viewCheck')}</Button></li>)}</ul>}{error && <p role="alert">{t('errors.requestFailed')}</p>}{Object.keys(finalizeFields).length > 0 && <ul role="alert" className="mt-2 text-sm">{Object.entries(finalizeFields).map(([field, reason]) => <li key={field}>{t(reason === 'positive' ? 'changeOrder.readiness.positive' : 'changeOrder.readiness.required', { field: t(readinessLabels[field as keyof typeof readinessLabels] ?? 'changeOrder.descriptionLabel') })}</li>)}</ul>}{selected && <article className="mt-6 rounded border bg-card p-4"><h3 className="font-semibold">{selected.summary}</h3>{selected.sourceKind === 'legacy_unverified' ? <p className="mt-3">{t('workflow.legacyHistory')}</p> : <>{workflow?.openHistory && <Button className="mt-3" disabled={busy || !!workflow.archived} variant="outline" onClick={() => { setBusy(true); void workflow.openHistory!(selected.id).catch(() => setError(true)).finally(() => setBusy(false)) }}>{t('workflow.reopen')}</Button>}<div className="mt-4">{selected.checkSnapshot.analysis ? <ScopeAssessment result={selected.checkSnapshot.analysis} request={selected.checkSnapshot.requestText} /> : <p className="whitespace-pre-wrap">{selected.checkSnapshot.requestText}</p>}</div><h4 className="mt-4 font-medium">{t('workflow.archivedScope')}</h4><p className="whitespace-pre-wrap">{selected.checkSnapshot.projectSnapshot?.scope}</p><h4 className="mt-4 font-medium">{t('reply.heading')}</h4><p className="whitespace-pre-wrap">{selected.checkSnapshot.draftDocument?.reply.text}</p>{selected.checkSnapshot.draftDocument?.changeOrder && <div className="mt-4"><ChangeOrderDocumentPreview draft={selected.checkSnapshot.draftDocument.changeOrder} /><Button className="mt-3" disabled={busy || !!workflow?.archived || agreements.some(item => item.status === 'finalized')} onClick={() => void finalize()}>{t('workflow.finalize')}</Button></div>}</>}{agreements.map(agreement => <AgreementItem key={`${agreement.id}:${agreement.revision}`} agreement={agreement} archived={!!workflow?.archived} refresh={() => refresh()} />)}</article>}</section>
}
