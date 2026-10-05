import type { Currency } from '@/lib/types'

export interface EditableDraft {
  aiValues?: Partial<Record<'description' | 'estimatedHours' | 'additionalCost' | 'currency' | 'timelineImpact' | 'rationale' | 'note', string>>
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
    title: 'CHANGE ORDER — DRAFT', date: 'Created', project: 'Project', client: 'Client', email: 'Client email',
    introduction: 'The following additional work is proposed for approval under the project above.',
    description: 'Requested change', hours: 'Estimated hours', cost: 'Additional cost', schedule: 'Schedule impact',
    endDate: 'Project end date', terms: 'Additional terms', rationale: 'Estimate rationale', note: 'Note',
    approval: 'Approved by', approvalDate: 'Date',
  },
  ru: {
    title: 'СОГЛАСОВАНИЕ ДОПОЛНИТЕЛЬНЫХ РАБОТ — ЧЕРНОВИК', date: 'Создан', project: 'Проект', client: 'Клиент', email: 'Email клиента',
    introduction: 'Предлагается согласовать следующие дополнительные работы по указанному проекту.',
    description: 'Запрошенное изменение', hours: 'Оценка часов', cost: 'Дополнительная стоимость', schedule: 'Влияние на сроки',
    endDate: 'Дата окончания проекта', terms: 'Дополнительные условия', rationale: 'Обоснование оценки', note: 'Примечание',
    approval: 'Согласовано', approvalDate: 'Дата',
  },
} as const

export function formatDocumentDate(value: string, language: 'ru' | 'en'): string {
  const date = new Date(`${value.slice(0, 10)}T00:00:00.000Z`)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(language === 'ru' ? 'ru-RU' : 'en-US', { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' }).format(date)
}

export function buildChangeOrderText(draft: EditableDraft): string {
  const t = labels[draft.language]
  const lines = [t.title, `${t.date}: ${formatDocumentDate(draft.createdAt, draft.language)}`, '', `${t.project}: ${draft.projectName}`]
  const add = (label: string, value: string) => { if (value.trim()) lines.push(`${label}: ${value.trim()}`) }
  add(t.client, draft.clientName)
  add(t.email, draft.clientEmail)
  lines.push('', t.introduction, '')
  add(t.description, draft.description)
  add(t.hours, draft.estimatedHours)
  add(t.cost, draft.additionalCost.trim() ? `${draft.additionalCost.trim()}${draft.currency ? ` ${draft.currency}` : ''}` : '')
  add(t.schedule, draft.timelineImpact)
  add(t.endDate, draft.endDate ? formatDocumentDate(draft.endDate, draft.language) : '')
  add(t.terms, draft.additionalTerms)
  add(t.rationale, draft.rationale)
  add(t.note, draft.note)
  lines.push('', `${t.approval}: ${draft.approvedBy}`, `${t.approvalDate}: ${draft.approvalDate}`)
  return lines.join('\n')
}
