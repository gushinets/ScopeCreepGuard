'use client'

import { RequestPanel } from './request-panel'
import { ResultPanel } from './result-panel'

export function ScopeCheckView() {
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)]">
      <div className="lg:sticky lg:top-24 lg:self-start">
        <RequestPanel />
      </div>
      <div>
        <ResultPanel />
      </div>
    </div>
  )
}
