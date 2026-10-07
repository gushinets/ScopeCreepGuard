'use client'

import { useState } from 'react'
import { AlertDialog } from '@base-ui/react/alert-dialog'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import type { Project } from '@/lib/types'
import { useStore } from './store'

export function DeleteProjectAction({ project, disabled = false }: { project: Project; disabled?: boolean }) {
  const t = useTranslations('projects')
  const { deleteProject } = useStore()
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const [failed, setFailed] = useState(false)

  async function remove() {
    if (pending) return
    setPending(true)
    setFailed(false)
    try {
      await deleteProject(project.id)
      setOpen(false)
    } catch { setFailed(true) }
    finally { setPending(false) }
  }

  return <AlertDialog.Root open={open} onOpenChange={next => { if (!pending) { setOpen(next); setFailed(false) } }}>
    <AlertDialog.Trigger aria-label={t('deleteLabel', { name: project.name })} disabled={disabled || pending} className="rounded-lg px-3 py-2 text-sm font-medium text-outscope-text hover:bg-outscope-soft focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50">{t('deleteProject')}</AlertDialog.Trigger>
    <AlertDialog.Portal>
      <AlertDialog.Backdrop className="fixed inset-0 z-40 bg-black/50" />
      <AlertDialog.Popup className="fixed left-1/2 top-1/2 z-50 w-[calc(100%_-_2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border border-border bg-card p-6 shadow-xl">
        <AlertDialog.Title className="text-lg font-semibold">{t('deleteTitle', { name: project.name })}</AlertDialog.Title>
        <AlertDialog.Description className="mt-3 text-sm text-muted-foreground">{t('deleteDescription')}</AlertDialog.Description>
        {failed && <p role="alert" className="mt-3 text-sm text-outscope-text">{t('deleteFailed')}</p>}
        <div className="mt-6 flex justify-end gap-2">
          <AlertDialog.Close disabled={pending} className="rounded-lg border border-border px-3 py-2 text-sm">{t('cancel')}</AlertDialog.Close>
          <Button type="button" variant="destructive" disabled={pending} onClick={() => void remove()}>{t(pending ? 'deleting' : 'deleteProject')}</Button>
        </div>
      </AlertDialog.Popup>
    </AlertDialog.Portal>
  </AlertDialog.Root>
}
