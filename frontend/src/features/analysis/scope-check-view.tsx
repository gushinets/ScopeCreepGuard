import { RequestPanel } from '@/features/analysis/request-panel'
import { ResultPanel } from '@/features/analysis/result-panel'
import { LegacyStateView } from '@/features/drafts'
import { useDrafts } from '@/features/drafts'

export function ScopeCheckView() {
  const { workflow } = { ...useDrafts() }
  if (workflow?.legacyRevision) return <LegacyStateView />
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)]">
      <div className="lg:sticky lg:top-24 lg:self-start">
        <RequestPanel />
      </div>
      <div><ResultPanel /></div>
    </div>
  )
}
