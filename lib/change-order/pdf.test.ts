import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { PDFDocument } from 'pdf-lib'
import { createChangeOrderPdf } from './pdf'
import type { EditableDraft } from './document'

const draft: EditableDraft = {
  createdAt: '2026-10-05T12:00:00Z', language: 'ru', projectName: 'Сайт', description: 'Дополнительные страницы',
  estimatedHours: '20', additionalCost: '10000', currency: 'RUB', timelineImpact: 'Неделя', rationale: '', note: '',
  clientName: '', clientEmail: '', endDate: '', additionalTerms: '', approvedBy: '', approvalDate: '',
}

describe('Change Order PDF', () => {
  it('creates a valid multi-page PDF for long Cyrillic text', async () => {
    const font = readFileSync('public/noto-sans.ttf')
    const bytes = await createChangeOrderPdf({ ...draft, description: 'Дополнительные страницы '.repeat(300) }, font)
    expect(Buffer.from(bytes).subarray(0, 5).toString()).toBe('%PDF-')
    // Full embedding avoids fontkit's broken Cyrillic positioning when a
    // variable font is subset. Keep this guard if the font or PDF stack changes.
    expect(bytes.byteLength).toBeGreaterThan(1_000_000)
    expect((await PDFDocument.load(bytes)).getPageCount()).toBeGreaterThan(1)
  }, 15_000)
})
