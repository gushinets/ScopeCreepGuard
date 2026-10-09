import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { PDFDocument } from 'pdf-lib'
import { getDocument } from 'pdfjs-dist/legacy/build/pdf.mjs'
import { createChangeOrderPdf } from './pdf'
import type { EditableDraft } from './document'
import { germanLabels } from './german-fixture'

const draft: EditableDraft = {
  createdAt: '2026-10-05T12:00:00Z', language: 'ru', projectName: 'Сайт', description: 'Дополнительные страницы',
  estimatedHours: '20', additionalCost: '10000', currency: 'RUB', timelineImpact: 'Неделя', rationale: '', note: '',
  providerName: '', clientName: '', clientEmail: '', endDate: '', additionalTerms: '', clientApproverName: '', approvalDate: '', noAdditionalCharge: false,
}

describe('Change Order PDF', () => {
  it('renders supported Ukrainian Cyrillic, including ґ, є, і and ї', async () => {
    const labels = {
      title: 'ДОДАТКОВЕ ЗАМОВЛЕННЯ', draft: 'ПРОЄКТ', documentNumber: 'Номер документа', created: 'Створено',
      project: 'Проєкт', provider: 'Виконавець', client: 'Замовник', clientEmail: 'Електронна пошта замовника',
      requestedChange: '1. Запитана зміна', commercialTerms: '2. Комерційні умови', estimatedEffort: 'Оцінка трудовитрат',
      additionalFee: 'Додаткова вартість', noAdditionalCharge: 'Без додаткової оплати', scheduleImpact: '3. Зміна строків',
      additionalTerms: '4. Додаткові умови', approval: '5. Погодження замовником', approvedBy: 'Погоджено', date: 'Дата',
      draftFooter: 'Проєкт для перевірки та погодження', introduction: 'Цей документ фіксує додаткові роботи після погодження замовником.',
      outsideScopeFree: 'Додаткові роботи буде виконано без додаткової оплати.', endDate: 'Нова дата завершення',
      rationale: 'Обґрунтування оцінки', terms: 'Особливі умови', note: 'Примітка', page: 'Сторінка', hours: 'годин',
    }
    const bytes = await createChangeOrderPdf({ ...draft, language: 'uk', changeOrderLabels: labels, projectName: 'Проєкт', description: 'Обґрунтовані зміни для української сторінки.', timelineImpact: 'Два дні', note: 'Проєкт для перевірки', noAdditionalCharge: true }, readFileSync('public/noto-sans.ttf'), readFileSync('public/noto-sans-bold.ttf'))
    const pdf = await getDocument({ data: bytes }).promise
    const content = await (await pdf.getPage(1)).getTextContent()
    const text = content.items.map((item) => 'str' in item ? item.str : '').join(' ')
    expect(text).toContain('ДОДАТКОВЕ ЗАМОВЛЕННЯ')
    expect(text).toContain('Обґрунтовані зміни для української сторінки.')
    expect(text).toContain('Без додаткової оплати')
    expect(text).toContain('Сторінка 1 /')
  }, 15_000)
  it.each(['ar', 'ja', 'zh', 'he', 'th', 'en-Arab'])('rejects unsupported %s before embedding or rendering', async (language) => {
    await expect(createChangeOrderPdf({ ...draft, language }, new Uint8Array(), new Uint8Array())).rejects.toThrow('unsupported_pdf_language')
  })
  it('rejects unsupported user-entered glyphs even under a supported language', async () => {
    await expect(createChangeOrderPdf({ ...draft, language: 'en', clientName: '日本語' }, readFileSync('public/noto-sans.ttf'), readFileSync('public/noto-sans-bold.ttf'))).rejects.toThrow('unsupported_pdf_glyph')
  }, 15_000)
  it('uses supplied German labels and preserves accented text', async () => {
    const bytes = await createChangeOrderPdf({ ...draft, language: 'de', changeOrderLabels: germanLabels, description: 'Zusätzliche Änderungen für Größe und Übersicht.', noAdditionalCharge: true }, readFileSync('public/noto-sans.ttf'), readFileSync('public/noto-sans-bold.ttf'))
    const pdf = await getDocument({ data: bytes }).promise
    const content = await (await pdf.getPage(1)).getTextContent()
    const text = content.items.map((item) => 'str' in item ? item.str : '').join(' ')
    expect(text).toContain('ÄNDERUNGSAUFTRAG')
    expect(text).toContain('Zusätzliche Änderungen für Größe und Übersicht.')
    expect(text).toContain('Ohne zusätzliche Vergütung')
    expect(text).toContain('GENEHMIGT VON')
    expect(text).toContain('Seite 1 /')
    expect(text).not.toContain('hours')
    expect(text).not.toContain('APPROVED BY')
  }, 15_000)
  it.each([
    ['ru', 'СОГЛАСОВАНО', 'ДАТА'],
    ['en', 'APPROVED BY', 'DATE'],
    ['es', 'APROBADO POR', 'FECHA'],
  ] as const)('renders empty %s approval fields', async (language, approverLabel, dateLabel) => {
    const bytes = await createChangeOrderPdf({ ...draft, language, clientApproverName: '', approvalDate: '' }, readFileSync('public/noto-sans.ttf'), readFileSync('public/noto-sans-bold.ttf'))
    const pdf = await getDocument({ data: bytes }).promise
    const texts = await Promise.all(Array.from({ length: pdf.numPages }, async (_, index) => {
      const content = await (await pdf.getPage(index + 1)).getTextContent()
      return content.items.map((item) => 'str' in item ? item.str : '').join(' ')
    }))
    expect(texts.join(' ')).toContain(approverLabel)
    expect(texts.join(' ')).toContain(dateLabel)
  }, 15_000)

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
