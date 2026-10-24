import { Popover } from '@base-ui/react/popover'
import { useRef, useState } from 'react'
import { useTranslations } from 'use-intl'
import { Button } from '@/shared/ui/button'
import { DEFAULT_DRAFT_FILTERS, validCreationDate, type DraftFilters } from './model/collection-client'

export function DraftFilterPopover({ filters, projects, onApply }: {
  filters: DraftFilters; projects: { id: string; name: string }[]; onApply: (filters: DraftFilters) => void
}) {
  const t = useTranslations('drafts')
  const [open, setOpen] = useState(false), [pending, setPending] = useState(filters), [invalid, setInvalid] = useState(false)
  const from = useRef<HTMLInputElement>(null), to = useRef<HTMLInputElement>(null)
  const inputClass = 'mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
  function apply(event: React.FormEvent) {
    event.preventDefault()
    if (pending.createdFrom && !validCreationDate(pending.createdFrom)) { setInvalid(true); from.current?.focus(); return }
    if (pending.createdTo && (!validCreationDate(pending.createdTo) || pending.createdFrom && pending.createdFrom > pending.createdTo)) { setInvalid(true); to.current?.focus(); return }
    onApply(pending); setOpen(false)
  }
  return <Popover.Root open={open} onOpenChange={next => { setOpen(next); if (next) { setPending(filters); setInvalid(false) } }}>
    <Popover.Trigger render={<Button type="button" variant="outline" />}>{t('filter')}</Popover.Trigger>
    <Popover.Portal><Popover.Positioner sideOffset={8} align="end" className="z-50">
      <Popover.Popup className="w-[calc(100vw-2rem)] max-w-sm rounded-xl border border-border bg-card p-4 shadow-lg">
        <Popover.Title className="mb-4 font-semibold">{t('filter')}</Popover.Title>
        <form onSubmit={apply} className="space-y-3" noValidate>
          <label className="block text-sm">{t('project')}<select className={inputClass} value={pending.projectId ?? ''} onChange={event => setPending({ ...pending, projectId: event.target.value || undefined })}>
            <option value="">{t('allProjects')}</option>
            {pending.projectId && !projects.some(project => project.id === pending.projectId) && <option value={pending.projectId}>{t('unavailableProject')}</option>}
            {projects.map(project => <option key={project.id} value={project.id}>{project.name}</option>)}
          </select></label>
          <label className="block text-sm">{t('createdFrom')}<input ref={from} className={inputClass} type="date" min="0001-01-01" max="9999-12-30" value={pending.createdFrom ?? ''} aria-invalid={invalid || undefined} aria-describedby={invalid ? 'draft-filter-error' : undefined} onChange={event => setPending({ ...pending, createdFrom: event.target.value || undefined })} /></label>
          <label className="block text-sm">{t('createdTo')}<input ref={to} className={inputClass} type="date" min="0001-01-01" max="9999-12-30" value={pending.createdTo ?? ''} aria-invalid={invalid || undefined} aria-describedby={invalid ? 'draft-filter-error' : undefined} onChange={event => setPending({ ...pending, createdTo: event.target.value || undefined })} /></label>
          <label className="block text-sm">{t('sort')}<select className={inputClass} value={pending.sort} onChange={event => setPending({ ...pending, sort: event.target.value === 'oldest' ? 'oldest' : 'newest' })}><option value="newest">{t('newest')}</option><option value="oldest">{t('oldest')}</option></select></label>
          {invalid && <p id="draft-filter-error" role="alert" className="text-sm text-outscope-text">{t('invalidFilters')}</p>}
          <div className="flex flex-wrap justify-between gap-2 pt-2"><Button type="button" variant="ghost" onClick={() => { onApply(DEFAULT_DRAFT_FILTERS); setOpen(false) }}>{t('clearFilters')}</Button><Button type="submit">{t('applyFilters')}</Button></div>
        </form>
      </Popover.Popup>
    </Popover.Positioner></Popover.Portal>
  </Popover.Root>
}
