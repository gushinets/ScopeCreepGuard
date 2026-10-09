import { describe, expect, it } from 'vitest'
import { ERROR_CODES } from '@/lib/api/errors'
import { MAX_SCOPE_FILE_BYTES, readScopeFile } from './read-file'

describe('readScopeFile', () => {
  it('reads a utf-8 text file', async () => {
    const file = new File(['Hello scope'], 'scope.txt', { type: 'text/plain' })
    await expect(readScopeFile(file)).resolves.toBe('Hello scope')
  })

  it('rejects oversized files before reading', async () => {
    const file = new File([new Uint8Array(MAX_SCOPE_FILE_BYTES + 1)], 'big.txt')
    await expect(readScopeFile(file)).rejects.toThrow(ERROR_CODES.scopeFileTooLarge)
  })

  it('rejects unsupported extensions', async () => {
    const file = new File(['x'], 'scope.docx')
    await expect(readScopeFile(file)).rejects.toThrow(
      ERROR_CODES.scopeFileUnsupported,
    )
  })

  it('rejects empty text extract', async () => {
    const file = new File(['   '], 'scope.md', { type: 'text/markdown' })
    await expect(readScopeFile(file)).rejects.toThrow(ERROR_CODES.scopeFileEmpty)
  })
})
