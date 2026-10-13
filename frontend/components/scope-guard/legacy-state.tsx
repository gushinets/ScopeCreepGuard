'use client'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { useStore } from './store'

export function LegacyStateView() {
  const { workflow } = useStore()
  const t = useTranslations()
  const state = workflow?.legacyRevision?.stateSnapshot
  if (!state) return null
  const context = state.legacy as { project_snapshot?: { scope?: string }; analysis_snapshot?: { summary?: string; reasoning?: string } } | undefined
  return <article className="mx-auto max-w-3xl rounded border bg-card p-5"><h2 className="text-xl font-semibold">{t('workflow.legacyImport')}</h2><p className="mt-2">{t('workflow.legacyHistory')}</p><p className="mt-4 whitespace-pre-wrap">{state.requestText}</p><h3 className="mt-4 font-medium">{t('workflow.archivedScope')}</h3><p className="whitespace-pre-wrap">{context?.project_snapshot?.scope ?? t('workflow.unknownScope')}</p><p className="mt-3">{context?.analysis_snapshot?.summary}</p><p>{context?.analysis_snapshot?.reasoning}</p><h3 className="mt-4 font-medium">{t('reply.heading')}</h3><p className="whitespace-pre-wrap">{state.draftDocument.reply.text}</p>{state.draftDocument.changeOrder && <section className="mt-4"><h3 className="font-medium">{t('changeOrder.heading')}</h3><p className="whitespace-pre-wrap">{state.draftDocument.changeOrder.description}</p><p>{state.draftDocument.changeOrder.estimatedHours} · {state.draftDocument.changeOrder.additionalCost} {state.draftDocument.changeOrder.currency}</p><p className="whitespace-pre-wrap">{state.draftDocument.changeOrder.additionalTerms}</p></section>}<Button className="mt-4" onClick={workflow?.closeLegacy}>{t('workflow.backToWorking')}</Button></article>
}
