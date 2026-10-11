import type { EditableDraft } from '@/lib/change-order/document'
import type { components } from './generated'
import { apiFetch, apiJson, ApiClientError } from './client'
import { ERROR_CODES } from './errors'

export type ExtractedScope = components['schemas']['ExtractionResponse']
export const MAX_SCOPE_FILE_BYTES = 5 * 1024 * 1024

export async function extractScope(file: File, signal?: AbortSignal): Promise<ExtractedScope> {
  if (file.size > MAX_SCOPE_FILE_BYTES) throw new ApiClientError(ERROR_CODES.scopeFileTooLarge, 413)
  const body = new FormData()
  body.append('file', file)
  return apiJson<ExtractedScope>('/api/scope/extract', { method: 'POST', body, signal })
}

export async function downloadChangeOrder(input: {
  draft: EditableDraft; projectId: string; draftId?: string | null; savedUnchanged?: boolean
}, signal?: AbortSignal): Promise<{ blob: Blob; filename: string }> {
  const response = input.draftId && input.savedUnchanged
    ? await apiFetch(`/api/drafts/${encodeURIComponent(input.draftId)}/pdf`, { cache: 'no-store', signal })
    : await apiFetch('/api/change-orders/pdf', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, signal,
      body: JSON.stringify({ projectId: input.projectId, ...(input.draftId ? { draftId: input.draftId } : {}), changeOrder: input.draft }),
    })
  if (response.headers.get('content-type')?.split(';')[0] !== 'application/pdf') {
    throw new ApiClientError(ERROR_CODES.pdfExportFailed, response.status)
  }
  const match = /filename="(change-order-[a-zA-Z0-9-]+\.pdf)"/.exec(response.headers.get('content-disposition') ?? '')
  return { blob: await response.blob(), filename: match?.[1] ?? 'change-order.pdf' }
}
