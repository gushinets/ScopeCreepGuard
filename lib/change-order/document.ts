import type { Currency } from '@/lib/types'

export type DocumentLanguage = 'ru' | 'en' | 'es'

export interface EditableDraft {
  aiValues?: Partial<Record<'description' | 'estimatedHours' | 'additionalCost' | 'currency' | 'timelineImpact' | 'rationale' | 'note', string>>
  reference?: string
  createdAt: string
  language: DocumentLanguage
  projectName: string
  description: string
  estimatedHours: string
  additionalCost: string
  currency: Currency | ''
  timelineImpact: string
  rationale: string
  note: string
  providerName: string
  clientName: string
  clientEmail: string
  endDate: string
  additionalTerms: string
  clientApproverName: string
  approvalDate: string
  noAdditionalCharge: boolean
}

interface ChangeOrderLabels {
  title: string; status: string; documentNumber: string; created: string
  project: string; provider: string; client: string; email: string; introduction: string
  requestedChange: string; commercialTerms: string; scheduleImpact: string; additionalTerms: string; approval: string
  effort: string; fee: string; noCharge: string; outsideScopeFree: string; endDate: string
  rationale: string; terms: string; note: string; approvedBy: string; date: string
  page: string; draftFooter: string
}

const labels: Record<DocumentLanguage, ChangeOrderLabels> = {
  en: {
    title: 'CHANGE ORDER', status: 'DRAFT', documentNumber: 'Document no.', created: 'Created',
    project: 'Project', provider: 'Provider', client: 'Client', email: 'Client email',
    introduction: 'This Change Order records additional work outside the agreed project scope. It becomes effective only after client approval.',
    requestedChange: '1. Requested change', commercialTerms: '2. Commercial terms', scheduleImpact: '3. Schedule impact', additionalTerms: '4. Additional terms', approval: '5. Client approval',
    effort: 'Estimated effort', fee: 'Additional fee', noCharge: 'No additional charge', outsideScopeFree: 'This work is outside the agreed scope and will be performed at no additional charge.', endDate: 'Revised project end date',
    rationale: 'Basis of estimate', terms: 'Special terms', note: 'Document note', approvedBy: 'Approved by', date: 'Date',
    page: 'Page', draftFooter: 'Draft - for review and approval',
  },
  ru: {
    title: 'СОГЛАСОВАНИЕ ДОПОЛНИТЕЛЬНЫХ РАБОТ', status: 'ЧЕРНОВИК', documentNumber: 'Номер документа', created: 'Создан',
    project: 'Проект', provider: 'Исполнитель', client: 'Клиент', email: 'Email клиента',
    introduction: 'Настоящий документ фиксирует дополнительные работы за пределами согласованного объёма проекта. Он вступает в силу только после согласования клиентом.',
    requestedChange: '1. Запрошенное изменение', commercialTerms: '2. Коммерческие условия', scheduleImpact: '3. Изменение сроков', additionalTerms: '4. Дополнительные условия', approval: '5. Согласование клиентом',
    effort: 'Оценка трудозатрат', fee: 'Дополнительная стоимость', noCharge: 'Без дополнительной оплаты', outsideScopeFree: 'Эта работа выходит за пределы согласованного объёма и будет выполнена без дополнительной оплаты.', endDate: 'Новая дата окончания проекта',
    rationale: 'Основание оценки', terms: 'Особые условия', note: 'Примечание к документу', approvedBy: 'Согласовано', date: 'Дата',
    page: 'Страница', draftFooter: 'Черновик - для проверки и согласования',
  },
  es: {
    title: 'ORDEN DE CAMBIO', status: 'BORRADOR', documentNumber: 'N.º de documento', created: 'Creado',
    project: 'Proyecto', provider: 'Proveedor', client: 'Cliente', email: 'Email del cliente',
    introduction: 'Esta Orden de Cambio documenta trabajo adicional fuera del alcance acordado del proyecto. Solo entra en vigor después de la aprobación del cliente.',
    requestedChange: '1. Cambio solicitado', commercialTerms: '2. Condiciones comerciales', scheduleImpact: '3. Impacto en el plazo', additionalTerms: '4. Condiciones adicionales', approval: '5. Aprobación del cliente',
    effort: 'Esfuerzo estimado', fee: 'Coste adicional', noCharge: 'Sin coste adicional', outsideScopeFree: 'Este trabajo está fuera del alcance acordado y se realizará sin coste adicional.', endDate: 'Nueva fecha de finalización',
    rationale: 'Base de la estimación', terms: 'Condiciones especiales', note: 'Nota del documento', approvedBy: 'Aprobado por', date: 'Fecha',
    page: 'Página', draftFooter: 'Borrador - para revisión y aprobación',
  },
}

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
  approval: { approverName: string; approvalDate: string }
}

export function formatDocumentDate(value: string, language: DocumentLanguage): string {
  const date = new Date(`${value.slice(0, 10)}T00:00:00.000Z`)
  if (Number.isNaN(date.getTime())) return value
  const locale = language === 'ru' ? 'ru-RU' : language === 'es' ? 'es-ES' : 'en-US'
  return new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' }).format(date)
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
  if (draft.providerName.trim()) metadata.push({ label: t.provider, value: draft.providerName.trim() })
  if (draft.clientName.trim()) metadata.push({ label: t.client, value: draft.clientName.trim() })
  if (draft.clientEmail.trim()) metadata.push({ label: t.email, value: draft.clientEmail.trim() })
  const commercialTerms: Array<{ label: string; value: string }> = []
  if (draft.estimatedHours.trim()) commercialTerms.push({ label: t.effort, value: `${draft.estimatedHours.trim()} ${draft.language === 'ru' ? 'ч' : draft.language === 'es' ? 'horas' : 'hours'}` })
  if (draft.noAdditionalCharge) commercialTerms.push({ label: t.fee, value: t.noCharge })
  else if (draft.additionalCost.trim()) commercialTerms.push({ label: t.fee, value: `${draft.additionalCost.trim()}${draft.currency ? ` ${draft.currency}` : ''}` })
  const additionalItems: Array<{ label: string; value: string }> = []
  if (draft.noAdditionalCharge) additionalItems.push({ label: t.fee, value: t.outsideScopeFree })
  if (draft.endDate) additionalItems.push({ label: t.endDate, value: formatDocumentDate(draft.endDate, draft.language) })
  if (draft.additionalTerms.trim()) additionalItems.push({ label: t.terms, value: draft.additionalTerms.trim() })
  if (draft.rationale.trim()) additionalItems.push({ label: t.rationale, value: draft.rationale.trim() })
  if (draft.note.trim()) additionalItems.push({ label: t.note, value: draft.note.trim() })
  return {
    labels: t, title: t.title, status: t.status, reference,
    createdDate: formatDocumentDate(draft.createdAt, draft.language), metadata,
    introduction: t.introduction, description: draft.description.trim(), commercialTerms,
    scheduleImpact: draft.timelineImpact.trim(), additionalItems,
    sections: [{ heading: t.requestedChange }, { heading: t.commercialTerms }, { heading: t.scheduleImpact }, { heading: t.additionalTerms }],
    approvalHeading: t.approval,
    approval: {
      approverName: draft.clientApproverName.trim(),
      approvalDate: draft.approvalDate ? formatDocumentDate(draft.approvalDate, draft.language) : '',
    },
  }
}

export function buildChangeOrderText(draft: EditableDraft): string {
  const document = createChangeOrderDocument(draft)
  const { labels: t } = document
  const lines = [
    `${document.title} — ${document.status}`,
    `${t.documentNumber}: ${document.reference}`,
    `${t.created}: ${document.createdDate}`,
    '', ...document.metadata.map(({ label, value }) => `${label}: ${value}`),
    '', document.introduction, '', document.sections[0].heading,
  ]
  if (document.description) lines.push(document.description)
  lines.push('', document.sections[1].heading)
  for (const item of document.commercialTerms) lines.push(`${item.label}: ${item.value}`)
  lines.push('', document.sections[2].heading)
  if (document.scheduleImpact) lines.push(document.scheduleImpact)
  lines.push('', document.sections[3].heading)
  for (const item of document.additionalItems) lines.push(`${item.label}: ${item.value}`)
  lines.push('', document.approvalHeading)
  lines.push(`${t.approvedBy}: ${document.approval.approverName}`)
  lines.push(`${t.date}: ${document.approval.approvalDate}`)
  return lines.join('\n').trimEnd()
}
