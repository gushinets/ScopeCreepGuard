<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

Store future implementation plans in `docs/architecture/plans/`. Follow that
directory's README for naming and handoff structure; `docs/plans.md` is a historical
document, not a plan directory. Inspect Git state and preserve unrelated local
changes before starting work.

## Docker startup and verification

- Use the README's explicit `compose.yaml` full-stack entry point or the
  `compose.{postgres,backend,frontend,llm-worker,export-worker}.yaml` component
  entry points. Do not invent feature-overlay combinations.
- Full end-to-end verification requires PostgreSQL, migrate, backend, app and both
  workers, with private test object storage. Component checks prove only their
  bounded scope, not full application readiness.
- Tests must use unique Compose project names and disposable databases/volumes.
  Never reset a database or remove a volume without explicit authorization.
- Use the one-shot migration gate and documented maintenance update sequence.
  API/workers must not mutate schemas during startup. Never bypass legacy
  adoption/backfill checks or set an overlay migration target.
- Before claiming verification, record the tested Git revision, local source
  changes, freshly built image IDs and revision labels. Preserve unrelated local
  files, especially untracked reports and evidence.
