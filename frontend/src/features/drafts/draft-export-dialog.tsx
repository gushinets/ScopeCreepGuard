import { Dialog } from '@base-ui/react/dialog'
import { useState } from 'react'
import { useLocale, useTranslations } from 'use-intl'
import { Button } from '@/shared/ui/button'
import { downloadDraftCollection, type DraftFilters } from './model/collection-client'

export function DraftExportDialog({ filters, disabled }: { filters: DraftFilters; disabled?: boolean }) {
  const t = useTranslations('drafts'), locale = useLocale()
  const [open, setOpen] = useState(false), [pending, setPending] = useState(false), [failed, setFailed] = useState(false)
  const [selection, setSelection] = useState(filters)
  async function download() {
    if (pending) return
    setPending(true); setFailed(false)
    try { await downloadDraftCollection(selection, locale === 'ru' ? 'ru' : 'en'); setOpen(false) }
    catch { setFailed(true) }
    finally { setPending(false) }
  }
  return <Dialog.Root open={open} onOpenChange={next => { if (!pending) { setOpen(next); setFailed(false); if (next) setSelection({ ...filters }) } }}>
    <Dialog.Trigger disabled={disabled} render={<Button type="button" variant="outline" />}>{t('export')}</Dialog.Trigger>
    <Dialog.Portal><Dialog.Backdrop className="fixed inset-0 z-40 bg-black/50" />
      <Dialog.Popup className="fixed left-1/2 top-1/2 z-50 w-[calc(100%_-_2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border border-border bg-card p-6 shadow-xl">
        <Dialog.Title className="text-lg font-semibold">{t('exportTitle')}</Dialog.Title>
        <Dialog.Description className="mt-3 text-sm text-muted-foreground">{t('exportDescription')}</Dialog.Description>
        {failed && <p role="alert" className="mt-3 text-sm text-outscope-text">{t('exportFailed')}</p>}
        <div className="mt-6 flex flex-wrap justify-end gap-2"><Dialog.Close disabled={pending} render={<Button type="button" variant="ghost" />}>{t('cancel')}</Dialog.Close><Button type="button" disabled={pending} onClick={() => void download()}>{t(pending ? 'exporting' : 'downloadCsv')}</Button></div>
      </Dialog.Popup>
    </Dialog.Portal>
  </Dialog.Root>
}
