import { ERROR_CODES } from '@/lib/api/errors'

export const MAX_SCOPE_FILE_BYTES = 5 * 1024 * 1024

function extensionOf(name: string) {
  const idx = name.lastIndexOf('.')
  if (idx < 0) return ''
  return name.slice(idx).toLowerCase()
}

async function readPdfText(file: File): Promise<string> {
  const pdfjs = await import('pdfjs-dist')
  // Worker for browser; Vitest/jsdom may not need full render — if worker fails in tests, only cover txt in unit tests and exercise PDF manually.
  pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url,
  ).toString()

  const data = new Uint8Array(await file.arrayBuffer())
  const doc = await pdfjs.getDocument({ data }).promise
  const parts: string[] = []
  for (let pageNum = 1; pageNum <= doc.numPages; pageNum += 1) {
    const page = await doc.getPage(pageNum)
    const content = await page.getTextContent()
    const text = content.items
      .map((item) => ('str' in item ? item.str : ''))
      .join(' ')
    parts.push(text)
  }
  return parts.join('\n')
}

export async function readScopeFile(file: File): Promise<string> {
  if (file.size > MAX_SCOPE_FILE_BYTES) {
    throw new Error(ERROR_CODES.scopeFileTooLarge)
  }

  const ext = extensionOf(file.name)
  let text = ''

  if (ext === '.txt' || ext === '.md') {
    text = await file.text()
  } else if (ext === '.pdf') {
    try {
      text = await readPdfText(file)
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'scope_pdf_extract_failed',
          message: error instanceof Error ? error.message : 'Unknown PDF error',
        }),
      )
      throw new Error(ERROR_CODES.scopeFileEmpty)
    }
  } else {
    throw new Error(ERROR_CODES.scopeFileUnsupported)
  }

  const trimmed = text.replace(/\u0000/g, '').trim()
  if (trimmed.length === 0) {
    throw new Error(ERROR_CODES.scopeFileEmpty)
  }
  return trimmed
}
