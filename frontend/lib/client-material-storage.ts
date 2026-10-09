import type { Locale } from '@/i18n/config'
import type { AnalysisResult, Project } from './types'
import { parseAnalysisResult } from './llm/schema'
import { parseClientMaterials, type ClientMaterials } from './client-materials'
import { readChangeOrder, writeChangeOrder } from './change-order/draft-storage'
import { mergeEstimate } from './change-order/merge-estimate'

const key = (userId: string, projectId: string, historyId: string) => `scg:client-materials:${userId}:${projectId}:${historyId}`
const activeKey = (userId: string) => `scg:client-materials:active:${userId}`
const context = (project: Project) => JSON.stringify([project.scope, project.industry, project.startDate, project.pricingModel, project.currency, project.hourlyRate, project.fixedPrice])

export function saveClientResult(userId: string, project: Project, historyId: string, request: string, locale: Locale, analysis: AnalysisResult, materials: ClientMaterials | null) {
  try {
    localStorage.setItem(key(userId, project.id, historyId), JSON.stringify({ version: 1, projectId: project.id, historyId, request, locale, context: context(project), analysis, materials }))
    localStorage.setItem(activeKey(userId), JSON.stringify({ projectId: project.id, historyId }))
    return true
  } catch { return false }
}

export function readClientResult(userId: string, project: Project, historyId: string, locale: Locale) {
  try {
    const raw = JSON.parse(localStorage.getItem(key(userId, project.id, historyId)) ?? 'null')
    const history = project.history.find((entry) => entry.id === historyId)
    if (!raw || raw.version !== 1 || raw.locale !== locale || raw.context !== context(project) || !history || history.request !== raw.request) return null
    const parsed = parseAnalysisResult(raw.analysis, locale)
    if (parsed.verdict !== history.verdict || parsed.summary !== history.summary) return null
    const analysis: AnalysisResult = {
      ...parsed,
      ...(typeof raw.analysis.draftCreatedAt === 'string' ? { draftCreatedAt: raw.analysis.draftCreatedAt } : {}),
      ...(typeof raw.analysis.commercialSignature === 'string' ? { commercialSignature: raw.analysis.commercialSignature } : {}),
      ...(typeof raw.analysis.estimateValid === 'boolean' ? { estimateValid: raw.analysis.estimateValid } : {}),
    }
    const materials = raw.materials ? parseClientMaterials(raw.materials) : null
    return { projectId: project.id, historyId, request: history.request, analysis, materials }
  } catch { return null }
}

export function readActiveClientResult(userId: string, projects: Project[], locale: Locale) {
  try {
    const pointer = JSON.parse(localStorage.getItem(activeKey(userId)) ?? 'null')
    const project = projects.find((item) => item.id === pointer?.projectId)
    return project && typeof pointer.historyId === 'string' ? readClientResult(userId, project, pointer.historyId, locale) : null
  } catch { return null }
}

export function clearActiveClientResult(userId: string) {
  try { localStorage.removeItem(activeKey(userId)) } catch { /* Storage is optional. */ }
}

/** Update existing drafts even if the editor is closed; never replace manual edits. */
export function updateSavedClientDraft(userId: string, projectId: string, historyId: string, materials: ClientMaterials, locale: Locale) {
  const saved = readChangeOrder(userId, projectId, historyId, locale)
  if (!saved || !materials.changeOrder) return
  const proposed = {
    ...saved, ...materials.changeOrder, language: materials.clientLanguage, changeOrderLabels: materials.changeOrderLabels,
    aiValues: { ...saved.aiValues, ...materials.changeOrder },
  }
  writeChangeOrder(userId, projectId, historyId, mergeEstimate(saved, proposed))
}
