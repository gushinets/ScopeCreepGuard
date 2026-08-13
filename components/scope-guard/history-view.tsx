'use client'

import { Clock } from 'lucide-react'
import { VerdictChip } from './verdict'
import { useStore } from './store'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function HistoryView() {
  const { selectedProject } = useStore()

  if (!selectedProject) {
    return (
      <div className="mx-auto max-w-2xl text-center text-sm text-muted-foreground">
        Select a project to see its check history.
      </div>
    )
  }

  const { history } = selectedProject

  return (
    <div className="mx-auto max-w-2xl">
      <h2 className="text-xl font-semibold text-foreground">History</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Previous checks for{' '}
        <span className="font-medium text-foreground">{selectedProject.name}</span>.
      </p>

      {history.length === 0 ? (
        <div className="mt-6 rounded-xl border border-dashed border-border bg-card/50 p-10 text-center">
          <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-muted">
            <Clock className="size-6 text-muted-foreground" aria-hidden="true" />
          </span>
          <h3 className="mt-4 text-base font-semibold text-foreground">
            No checks yet
          </h3>
          <p className="mx-auto mt-1.5 max-w-sm text-sm text-muted-foreground text-pretty">
            Once you check a client request for this project, it&apos;ll show up here.
          </p>
        </div>
      ) : (
        <ul className="mt-6 flex flex-col gap-3">
          {history.map((h) => (
            <li
              key={h.id}
              className="rounded-lg border border-border bg-card p-4"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs text-muted-foreground">
                  {formatDate(h.date)}
                </span>
                <VerdictChip verdict={h.verdict} />
              </div>
              <p className="mt-2 text-sm leading-relaxed text-foreground text-pretty">
                {h.request}
              </p>
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground text-pretty">
                {h.summary}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
