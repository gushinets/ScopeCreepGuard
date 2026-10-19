import type { components } from '@/shared/api/generated'
import { apiJson, ApiClientError } from '@/shared/api/client'
import { ERROR_CODES } from '@/shared/api/errors'
export type ExtractedScope = components['schemas']['ExtractionResponse']
export const MAX_SCOPE_FILE_BYTES = 5 * 1024 * 1024

export async function extractScope(file: File, signal?: AbortSignal): Promise<ExtractedScope> {
  if (file.size > MAX_SCOPE_FILE_BYTES) throw new ApiClientError(ERROR_CODES.scopeFileTooLarge, 413)
  const body = new FormData()
  body.append('file', file)
  return apiJson<ExtractedScope>('/api/scope/extract', { method: 'POST', body, signal })
}
