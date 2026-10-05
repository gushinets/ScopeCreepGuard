import type { Currency } from '@/lib/types'

export interface EditableDraft {
  aiValues?: Partial<Record<'description' | 'estimatedHours' | 'additionalCost' | 'currency' | 'timelineImpact' | 'rationale' | 'note', string>>
  reference?: string
  createdAt: string
  language: 'ru' | 'en'
  projectName: string
  description: string
  estimatedHours: string
  additionalCost: string
  currency: Currency | ''
  timelineImpact: string
  rationale: string
  note: string
  clientName: string
  clientEmail: string
  endDate: string
  additionalTerms: string
  approvedBy: string
  approvalDate: string
}

const labels = {
  en: {
    title: 'CHANGE ORDER', status: 'DRAFT', documentNumber: 'Document no.', created: 'Created',
    project: 'Project', client: 'Client', email: 'Client email',
    introduction: 'This Change Order records the additional work proposed for the project identified below. It becomes effective only after approval by both parties.',
    requestedChange: '1. Requested change', commercialTerms: '2. Commercial terms',
    scheduleImpact: '3. Schedule impact', additionalTerms: '4. Additional terms', approval: '5. Approval',
    effort: 'Estimated effort', fee: 'Additional fee', endDate: 'Revised project end date',
    rationale: 'Basis of estimate', terms: 'Special terms', note: 'Document note',
    provider: 'Provider', clientSignature: 'Client', signature: 'Signature / name', date: 'Date',
    page: 'Page', draftFooter: 'Draft - for review and approval', notProvided: 'Not specified',
  },
  ru: {
    title: 'СОГЛАСОВАНИЕ ДОПОЛНИТЕЛЬНЫХ РАБОТ', status: 'ЧЕРНОВИК', documentNumber: 'Номер документа', created: 'Создан',
    project: 'Проект', client: 'Клиент', email: 'Email клиента',
    introduction: 'Настоящий документ фиксирует дополнительные работы, предлагаемые по указанному ниже проекту. Он вступает в силу только после согласования обеими сторонами.',
    requestedChange: '1. Запрошенное изменение', commercialTerms: '2. Коммерческие условия',
    scheduleImpact: '3. Изменение сроков', additionalTerms: '4. Дополнительные условия', approval: '5. Согласование',
    effort: 'Оценка трудозатрат', fee: 'Дополнительная стоимость', endDate: 'Новая дата окончания проекта',
    rationale: 'Основание оценки', terms: 'Особые условия', note: 'Примечание к документу',
    provider: 'Исполнитель', clientSignature: 'Клиент', signature: 'Подпись / ФИО', date: 'Дата',
    page: 'Страница', draftFooter: 'Черновик - для проверки и согласования', notProvided: 'Не указано',
  },
} as const

export type ChangeOrderLabels = typeof labels.en | typeof labels.ru

export interface ChangeOrderDocument {
  labels: ChangeOrderLabels
  title: string
  status: string
  reference: string
  createdDate: string
  metadata: Array<{ label: string; value: string }>
  introduction: string
  description: string
  commercialTerms: Array<{ label: string; value: string }>
  scheduleImpact: string
  additionalItems: Array<{ label: string; value: string }>
  sections: Array<{ heading: string }>
  approvalHeading: string
  signatures: Array<{ label: string; name: string; date: string }>
}

export function formatDocumentDate(value: string, language: 'ru' | 'en'): string {
  const date = new Date(`${value.slice(0, 10)}T00:00:00.000Z`)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(language === 'ru' ? 'ru-RU' : 'en-US', { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' }).format(date)
}

export function makeChangeOrderReference(createdAt: string, historyId: string): string {
  const date = createdAt.slice(0, 10).replace(/-/g, '') || 'DRAFT'
  const suffix = historyId.replace(/[^a-zA-Z0-9]/g, '').slice(-6).toUpperCase() || 'DRAFT'
  return `CO-${date}-${suffix}`
}

export function createChangeOrderDocument(draft: EditableDraft): ChangeOrderDocument {
  const t = labels[draft.language]
  const reference = draft.reference?.trim() || `CO-${draft.createdAt.slice(0, 10).replace(/-/g, '')}`
  const metadata: Array<{ label: string; value: string }> = [{ label: t.project, value: draft.projectName.trim() }]
  if (draft.clientName.trim()) metadata.push({ label: t.client, value: draft.clientName.trim() })
  if (draft.clientEmail.trim()) metadata.push({ label: t.email, value: draft.clientEmail.trim() })
  const commercialTerms: Array<{ label: string; value: string }> = []
  if (draft.estimatedHours.trim()) commercialTerms.push({ label: t.effort, value: `${draft.estimatedHours.trim()} ${draft.language === 'ru' ? 'ч' : 'hours'}` })
  if (draft.additionalCost.trim()) commercialTerms.push({ label: t.fee, value: `${draft.additionalCost.trim()}${draft.currency ? ` ${draft.currency}` : ''}` })
  const additionalItems: Array<{ label: string; value: string }> = []
  if (draft.endDate) additionalItems.push({ label: t.endDate, value: formatDocumentDate(draft.endDate, draft.language) })
  if (draft.additionalTerms.trim()) additionalItems.push({ label: t.terms, value: draft.additionalTerms.trim() })
  if (draft.rationale.trim()) additionalItems.push({ label: t.rationale, value: draft.rationale.trim() })
  if (draft.note.trim()) additionalItems.push({ label: t.note, value: draft.note.trim() })
  return {
    labels: t,
    title: t.title,
    status: t.status,
    reference,
    createdDate: formatDocumentDate(draft.createdAt, draft.language),
    metadata,
    introduction: t.introduction,
    description: draft.description.trim(),
    commercialTerms,
    scheduleImpact: draft.timelineImpact.trim(),
    additionalItems,
    sections: [{ heading: t.requestedChange }, { heading: t.commercialTerms }, { heading: t.scheduleImpact }, { heading: t.additionalTerms }],
    approvalHeading: t.approval,
    signatures: [
      { label: t.provider, name: draft.approvedBy.trim(), date: draft.approvalDate },
      { label: t.clientSignature, name: '', date: '' },
    ],
  }
}

export function buildChangeOrderText(draft: EditableDraft): string {
  const document = createChangeOrderDocument(draft)
  const { labels: t } = document
  const lines = [
    `${document.title} — ${document.status}`,
    `${t.documentNumber}: ${document.reference}`,
    `${t.created}: ${document.createdDate}`,
    '',
    ...document.metadata.map(({ label, value }) => `${label}: ${value}`),
    '',
    document.introduction,
    '',
    document.sections[0].heading,
  ]
  if (document.description) lines.push(document.description)
  lines.push('', document.sections[1].heading)
  for (const item of document.commercialTerms) lines.push(`${item.label}: ${item.value}`)
  lines.push('', document.sections[2].heading)
  if (document.scheduleImpact) lines.push(document.scheduleImpact)
  lines.push('', document.sections[3].heading)
  for (const item of document.additionalItems) lines.push(`${item.label}: ${item.value}`)
  lines.push('', document.approvalHeading)
  for (const signature of document.signatures) {
    lines.push(`${signature.label}: ${signature.name}`, `${t.signature}:`, `${t.date}: ${signature.date}`, '')
  }
  return lines.join('\n').trimEnd()
}
