import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { PDFDocument } from 'pdf-lib'
import { getDocument } from 'pdfjs-dist/legacy/build/pdf.mjs'
import { createChangeOrderPdf } from './pdf'
import type { EditableDraft } from './document'

const draft: EditableDraft = {
  createdAt: '2026-10-05T12:00:00Z', language: 'ru', projectName: 'Сайт', description: 'Дополнительные страницы',
  estimatedHours: '20', additionalCost: '10000', currency: 'RUB', timelineImpact: 'Неделя', rationale: '', note: '',
  providerName: '', clientName: '', clientEmail: '', endDate: '', additionalTerms: '', clientApproverName: '', approvalDate: '', noAdditionalCharge: false,
}

describe('Change Order PDF', () => {
  it('renders the client approver and approval date entered by the user', async () => {
    const font = readFileSync('public/noto-sans.ttf')
    const boldFont = readFileSync('public/noto-sans-bold.ttf')
    const bytes = await createChangeOrderPdf({
      ...draft,
      language: 'en',
      clientApproverName: 'Ana Ruiz',
      approvalDate: '2026-10-06',
    }, font, boldFont)
    const pdf = await getDocument({ data: bytes }).promise
    const content = await (await pdf.getPage(1)).getTextContent()
    const text = content.items.map((item) => 'str' in item ? item.str : '').join(' ')

    expect(text).toContain('APPROVED BY')
    expect(text).toContain('Ana Ruiz')
    expect(text).toContain('October 6, 2026')
  }, 15_000)

  it('keeps a typical complete draft on one page', async () => {
    const font = readFileSync('public/noto-sans.ttf')
    const boldFont = readFileSync('public/noto-sans-bold.ttf')
    const bytes = await createChangeOrderPdf({
      ...draft,
      reference: 'CO-20261005-A1B2C3',
      description: 'Разработка дополнительной страницы с формой заявки и адаптивной версткой.',
      clientName: 'ООО «Север»',
      clientEmail: 'hello@example.com',
      rationale: 'Работа не входит в согласованный объем проекта.',
      note: 'Работы начинаются после письменного согласования.',
      additionalTerms: 'Оплата в течение пяти рабочих дней после согласования.',
    }, font, boldFont)

    expect((await PDFDocument.load(bytes)).getPageCount()).toBe(1)
  }, 15_000)

  it('creates a valid multi-page PDF for long Cyrillic text', async () => {
    const font = readFileSync('public/noto-sans.ttf')
    const boldFont = readFileSync('public/noto-sans-bold.ttf')
    const bytes = await createChangeOrderPdf({ ...draft, reference: 'CO-20261005-A1B2C3', description: 'Дополнительные страницы '.repeat(300) }, font, boldFont)
    expect(Buffer.from(bytes).subarray(0, 5).toString()).toBe('%PDF-')
    // Full embedding avoids fontkit's broken Cyrillic positioning when a
    // variable font is subset. Keep this guard if the font or PDF stack changes.
    expect(bytes.byteLength).toBeGreaterThan(1_000_000)
    expect((await PDFDocument.load(bytes)).getPageCount()).toBeGreaterThan(1)
  }, 15_000)
})
