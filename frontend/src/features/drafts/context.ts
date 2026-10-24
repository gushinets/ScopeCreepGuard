import { featureContext } from '@/shared/ui/feature-context'
import type { DraftEditor } from './editor'
import type { DraftDocument } from './model/types'
import type { DraftCollection, DraftFilters } from './model/collection-client'
import type { Locale } from '@/shared/i18n/config'

export interface DraftsValue {
  draftProjects: { id: string; name: string }[]
  draftDocument: DraftDocument | null; currentDraftId: string | null; draftSessionId: string
  draftError: DraftEditor['draftError']; isSavingDraft: boolean; isDraftDirty: boolean
  requestText: string; setRequestText: DraftEditor['setRequestText']; loadExample: DraftEditor['setRequestText']
  updateReply: DraftEditor['updateReply']; updateChangeOrder: DraftEditor['updateChangeOrder']
  saveDraft: () => Promise<unknown>; openDraft: (id: string) => Promise<void>
  listDrafts: (filters: DraftFilters, page: { limit: number; offset: number }) => Promise<DraftCollection>
  exportCurrentDraft: (locale: Locale) => Promise<void>
  workflow: {
    status: DraftEditor['saveStatus']; stale: boolean; recovery: DraftEditor['recovery']
    acceptRecovery: DraftEditor['acceptRecovery']; discardRecovery: DraftEditor['discardRecovery']
    retrySave: () => Promise<unknown>; resolveConflict: DraftEditor['resolveConflict']; compareConflict: DraftEditor['compareConflict']
    legacyRevision: DraftEditor['legacyRevision']; closeLegacy: () => void; archived: boolean
  }
}
export const [DraftsContext, useDrafts] = featureContext<DraftsValue>('Draft editor')
