import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { PDFDocument } from 'pdf-lib'
import { describe, expect, it } from 'vitest'
import { createChangeOrderPdf } from '@/lib/change-order/pdf'
import type { DocumentLanguage, EditableDraft } from '@/lib/change-order/document'

const base = (language: DocumentLanguage): EditableDraft => ({
  reference: `CO-20261005-${language.toUpperCase()}`,
  createdAt: '2026-10-05T12:00:00Z', language, projectName: 'Sitio web de «Север»',
  providerName: 'North Studio LLC', clientName: 'Acme España', clientEmail: 'ana@example.com',
  description: 'Añadir una sección de noticias con búsqueda, categorías y diseño adaptable.',
  estimatedHours: '24', additionalCost: '120000', currency: 'EUR',
  timelineImpact: 'La fecha de entrega cambia en ocho días laborables después de la aprobación.',
  rationale: 'Esta función no forma parte del alcance acordado.',
  note: 'Borrador para revisión y aprobación.', endDate: '2026-11-15',
  additionalTerms: 'El trabajo comienza después de la aprobación escrita.',
  clientApproverName: 'Ana Ruiz', approvalDate: '2026-10-06', noAdditionalCharge: false,
})

describe('Change Order PDF visual fixtures', () => {
  it('writes representative Russian, English, and Spanish PDFs with expected pagination', async () => {
    const regular = await readFile('public/noto-sans.ttf')
    const bold = await readFile('public/noto-sans-bold.ttf')
    const russian = { ...base('ru'), description: 'Добавить раздел новостей с поиском, категориями и адаптивной вёрсткой.', timelineImpact: 'Срок увеличится на восемь рабочих дней.', rationale: 'Функция не входит в согласованный объём.', note: 'Черновик для проверки.', additionalTerms: 'Работы начнутся после письменного согласования.' }
    const longRussian = { ...russian, description: 'Дополнительные работы с подробным описанием. '.repeat(180), additionalCost: '1234567890123456789012345678901234567890' }
    const english = { ...base('en'), description: 'Add a searchable news section with categories and responsive layouts.', timelineImpact: 'Delivery moves by eight business days after approval.', rationale: 'This feature is outside the agreed scope.', note: 'Draft for review.', additionalTerms: 'Work begins after written approval.' }
    const spanish = { ...base('es'), noAdditionalCharge: true }
    const fixtures = { 'change-order-ru-one-page.pdf': russian, 'change-order-ru-long.pdf': longRussian, 'change-order-en.pdf': english, 'change-order-es.pdf': spanish }

    await mkdir('output/pdf/verification', { recursive: true })
    for (const [name, draft] of Object.entries(fixtures)) {
      const bytes = await createChangeOrderPdf(draft, regular, bold)
      await writeFile(`output/pdf/verification/${name}`, bytes)
      const pages = (await PDFDocument.load(bytes)).getPageCount()
      if (name === 'change-order-ru-long.pdf') expect(pages).toBeGreaterThan(1)
      else expect(pages).toBe(1)
    }
  }, 30_000)
})
