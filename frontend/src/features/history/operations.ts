import { useTranslations } from 'use-intl'
import { type DraftEditor, type WorkflowOperations, type WorkingDraft, type ArchivedCheck } from '@/features/drafts'
import { featureContext } from '@/shared/ui/feature-context'

export function useHistoryCommands(editor: DraftEditor, commands: WorkflowOperations, onEntry: (entry: ArchivedCheck) => void, showCheck: () => void) {
  const t = useTranslations()
  async function complete() {
    const saved = await editor.flush()
    const response = await commands.run<{ entry: ArchivedCheck }>(`drafts/${saved.id}/history`, { expectedRevision: saved.revision })
    editor.setHistoryId(response.entry.id)
    onEntry({ ...response.entry, projectId: response.entry.projectId ?? saved.projectId })
  }
  async function openHistory(identifier: string) {
    if (!window.confirm(t('workflow.confirmReopen'))) return
    const saved = await editor.flush()
    const run = editor.navigation.current
    const restored = await commands.run<{ draft: WorkingDraft }>(`history/${identifier}/restore`, { expectedRevision: saved.revision })
    if (run === editor.navigation.current) { editor.install(restored.draft); editor.setHistoryId(identifier); showCheck() }
  }
  return { complete, openHistory }
}
export const [HistoryContext, useHistory] = featureContext<ReturnType<typeof useHistoryCommands>>('History')
