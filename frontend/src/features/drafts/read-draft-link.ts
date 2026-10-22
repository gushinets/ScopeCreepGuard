import { workflowApi, WorkflowApiError } from './model/workflow-client'
import type { WorkingDraft, WorkingRevision } from './model/workflow-types'

type LegacyLink = WorkingRevision & { projectId: string }

/** A 404 also represents a draft belonging to another account; never bypass it. */
export async function readDraftLink(id: string): Promise<{ draft: WorkingDraft; legacy: LegacyLink | null } | null> {
  try {
    return { ...(await workflowApi<{ draft: WorkingDraft }>(`drafts/${encodeURIComponent(id)}`)), legacy: null }
  } catch (failure) {
    if (!(failure instanceof WorkflowApiError) || failure.status !== 404) throw failure
  }
  let legacy: LegacyLink
  try {
    legacy = (await workflowApi<{ revision: LegacyLink }>(`legacy-drafts/${encodeURIComponent(id)}`)).revision
  } catch (failure) {
    if (!(failure instanceof WorkflowApiError) || failure.status !== 404) throw failure
    return null
  }
  const { draft } = await workflowApi<{ draft: WorkingDraft }>(`projects/${legacy.projectId}/draft`)
  return { draft, legacy }
}
