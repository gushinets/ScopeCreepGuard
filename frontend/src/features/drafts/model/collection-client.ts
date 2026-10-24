import { apiFetch } from '@/shared/api/client'
import type { components } from '@/shared/api/generated'
import type { Locale } from '@/shared/i18n/config'

export interface DraftFilters { projectId?: string; createdFrom?: string; createdTo?: string; sort: 'newest' | 'oldest' }
export type DraftCollection = components['schemas']['DraftCollectionResponse']
export const DEFAULT_DRAFT_FILTERS: DraftFilters = { sort: 'newest' }
const keys = ['draftProject', 'draftCreatedFrom', 'draftCreatedTo', 'draftSort', 'draftPage']
export function validCreationDate(value: string) {
  const instant = new Date(`${value}T00:00:00Z`)
  return /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value) && value >= '0001-01-01' && value <= '9999-12-30' &&
    Number.isFinite(instant.getTime()) && instant.toISOString().slice(0, 10) === value
}
export function readDraftFilters(query: URLSearchParams) {
  const projectId = query.get('draftProject') ?? undefined
  const createdFrom = query.get('draftCreatedFrom') ?? undefined
  const createdTo = query.get('draftCreatedTo') ?? undefined
  const sort = query.get('draftSort') ?? 'newest'
  const page = query.get('draftPage') ?? '1'
  const invalid = !!(projectId !== undefined && !/^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(projectId) ||
    createdFrom !== undefined && !validCreationDate(createdFrom) || createdTo !== undefined && !validCreationDate(createdTo) ||
    createdFrom && createdTo && createdFrom > createdTo || !['newest', 'oldest'].includes(sort) || !/^[1-9][0-9]*$/.test(page) || !Number.isSafeInteger(Number(page)) || Number(page) > Math.floor(Number.MAX_SAFE_INTEGER / 50))
  const filters: DraftFilters = { ...(projectId ? { projectId } : {}), ...(createdFrom ? { createdFrom } : {}), ...(createdTo ? { createdTo } : {}), sort: sort === 'oldest' ? 'oldest' : 'newest' }
  return { filters, invalid, offset: (Number(page) - 1) * 50 }
}
export function writeDraftFilters(current: URLSearchParams, filters: DraftFilters, offset = 0) {
  const query = new URLSearchParams(current)
  keys.forEach(key => query.delete(key))
  if (filters.projectId) query.set('draftProject', filters.projectId)
  if (filters.createdFrom) query.set('draftCreatedFrom', filters.createdFrom)
  if (filters.createdTo) query.set('draftCreatedTo', filters.createdTo)
  if (filters.sort !== 'newest') query.set('draftSort', filters.sort)
  if (offset) query.set('draftPage', String(offset / 50 + 1))
  return query
}
export function draftQuery(filters: DraftFilters) {
  const query = new URLSearchParams()
  if (filters.projectId) query.set('projectId', filters.projectId)
  if (filters.createdFrom) query.set('createdFrom', filters.createdFrom)
  if (filters.createdTo) query.set('createdTo', filters.createdTo)
  query.set('sort', filters.sort)
  return query
}
export async function fetchDraftCollection(filters: DraftFilters, page: { limit: number; offset: number }): Promise<DraftCollection> {
  const query = draftQuery(filters)
  query.set('limit', String(page.limit)); query.set('offset', String(page.offset))
  return (await apiFetch(`/api/v2/drafts?${query}`, { cache: 'no-store' })).json() as Promise<DraftCollection>
}
async function download(path: string, filename: string, stillCurrent: () => boolean = () => true) {
  const response = await apiFetch(path, { cache: 'no-store' })
  const blob = await response.blob()
  if (!stillCurrent()) throw new Error('Draft changed during export')
  const url = URL.createObjectURL(blob)
  try {
    const link = document.createElement('a')
    link.href = url; link.download = filename; document.body.append(link); link.click(); link.remove()
  } finally { setTimeout(() => URL.revokeObjectURL(url), 1000) }
}
export function downloadDraftCollection(filters: DraftFilters, locale: Locale) {
  const query = draftQuery(filters); query.set('locale', locale)
  return download(`/api/v2/drafts/export.csv?${query}`, `drafts-${locale}.csv`)
}
export function downloadDraftCsv(id: string, locale: Locale, revision: string, stillCurrent: () => boolean) {
  const query = new URLSearchParams({ locale, expectedRevision: revision })
  return download(`/api/v2/drafts/${encodeURIComponent(id)}/export.csv?${query}`, `draft-${id}-${locale}.csv`, stillCurrent)
}
