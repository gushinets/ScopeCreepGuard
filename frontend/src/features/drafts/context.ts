import { featureContext } from '@/shared/ui/feature-context'
import type { DraftEditor } from './editor'
import type { DraftDocument, DraftListItem } from './model/types'

export interface DraftsValue {
  draftDocument: DraftDocument | null; currentDraftId: string | null; draftSessionId: string
  draftError: DraftEditor['draftError']; isSavingDraft: boolean; isDraftDirty: boolean
  requestText: string; setRequestText: DraftEditor['setRequestText']; loadExample: DraftEditor['setRequestText']
  updateReply: DraftEditor['updateReply']; updateChangeOrder: DraftEditor['updateChangeOrder']
  saveDraft: () => Promise<unknown>; openDraft: (id: string) => Promise<void>; listDrafts: () => Promise<DraftListItem[]>
  workflow: {
    status: DraftEditor['saveStatus']; stale: boolean; recovery: DraftEditor['recovery']
    acceptRecovery: DraftEditor['acceptRecovery']; discardRecovery: DraftEditor['discardRecovery']
    retrySave: () => Promise<unknown>; resolveConflict: DraftEditor['resolveConflict']; compareConflict: DraftEditor['compareConflict']
    legacyRevision: DraftEditor['legacyRevision']; closeLegacy: () => void; archived: boolean
  }
}
export const [DraftsContext, useDrafts] = featureContext<DraftsValue>('Draft editor')
