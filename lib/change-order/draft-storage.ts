import type { EditableDraft } from './document'

const key = (userId: string, projectId: string, historyId: string) => `scg:change-order:${userId}:${projectId}:${historyId}`

export function readChangeOrder(userId: string, projectId: string, historyId: string): EditableDraft | null {
  try {
    const raw = localStorage.getItem(key(userId, projectId, historyId))
    if (!raw) return null
    const value: unknown = JSON.parse(raw)
    if (!value || typeof value !== 'object' || Array.isArray(value)) return null
    const draft = value as EditableDraft
    if (draft.language !== 'ru' && draft.language !== 'en' && draft.language !== 'es') return null
    if (typeof draft.createdAt !== 'string' || typeof draft.projectName !== 'string' || typeof draft.description !== 'string') return null
    return draft
  } catch { return null }
}

export function writeChangeOrder(userId: string, projectId: string, historyId: string, draft: EditableDraft): void {
  try { localStorage.setItem(key(userId, projectId, historyId), JSON.stringify(draft)) }
  catch { /* In-memory editing and export still work. */ }
}
