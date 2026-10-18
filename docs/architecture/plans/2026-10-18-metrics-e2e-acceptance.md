# User collection and marketing metrics acceptance

## Identity and checkout

- Requested acceptance, no issue mutation. Branch `codex/metrics-e2e-acceptance`, current checkout, no worktree, stash, reset, commit, push or product changes.
- Origin fetched 2026-10-18 Europe/Moscow. Test SHA: `3084c1049432ccfa8996b3c9bde10b9ecaaa3fc6` (`origin/main`). Feature commits 2714cd6/37df435 have byte-identical trees to main commits 74a9c73/29c67f4, respectively; ancestry alone would miss this integration.
- Initial checkout f1cd5af on codex/restore-scope-assessment-and-language had eight unrelated untracked documents; preserve all. AGENT.md and WORKLOG.md are ignored.

## Definitions established before execution

Authority: design/profile-behavior-marketing-metrics.md including resolved section 11; original implementation plan; architecture/marketing-metrics.md; current source. Technical identity is users.id, activity identity profiles.id with UNIQUE user_id, projects carry matching user/profile ownership. Sessions use signed opaque browser identity, per profile/browser, 30-minute inactivity, shared tabs with Web Locks; no duration KPI. UTC days and half-open intervals apply regardless of profile timezone.

- Activity: successful baseline analysis with explicit saved History or finalized CO. Login, browse, project creation, autosave, regeneration, translation, estimates and PDF alone do not activate activity. First saved check within [registration, registration+7 days) activates; mature seven-day registrations alone enter activation denominator/numerator. TTV includes later first checks.
- DAU distinct profiles today; MAU reporting day plus preceding 29 UTC days; PQL >=3 distinct saved checks and >=1 finalized CO in that window. Retention exact calendar D7/D30 after timely activation, current-day percentage NULL. Adoption intersects same-day function users with DAU.
- Success: durable terminal outcome; saved check additionally requires explicit History. Distinct command keys mean intentional operations, equal text may count again. Same-key replay must retain one receipt/result; changed content conflicts. Events use source/deduplication_key uniqueness; immutable facts. Durations from admission to terminal including queue/retries; continuous interpolated median/P95. Starts use admission day, outcomes terminal day; empty rates NULL.
- T1 persists result/source facts; dirty commit closes T1 before synchronous independent T2. Global lock then single source snapshot, full-history recomputation/upsert. Next dirty action or supported MetricsService.read/reconcile repairs missed updates. Direct reads may be stale; no periodic recovery worker or HTTP marketing route.
- Final table includes confirmed physical AI calls/retries/tokens/estimated costs/validation (original plan explicit decisions). Calls assigned to UTC start day; missing observations yield NULL totals with unknown counts. PDF metrics, admin, external analytics, new workers, session duration, CRM, billing and inferred traits excluded.
- Current source includes `agreement` in aggregate operation totals while the metric definition still names four kinds. Verify and report this discrepancy; do not silently redefine agreed scope.

## Ordered execution

1. Read collection entry points, migrations, repositories, current calculation and scope decisions; capture exact source fingerprints.
2. Provision owned isolated PostgreSQL, migrate only it. Launch API, existing LLM worker role with controlled provider adapter and frontend from tested sources at unused loopback ports. No paid/live AI calls. Verify readiness/code provenance.
3. Record before/after independent database snapshots around real UI registration/login/browse/project/check/intentional repeat/CO/reopen/refresh/two-tab/double-click journeys and second-account isolation. Supplement UI with authenticated API exact-key replay and controlled failures.
4. Cause T2 write failure in the owned database after successful product persistence, preserve first failure, prove result retrieval and repair/repeated reconciliation without double counts.
5. Compare every final column with separate SQL reference calculations over source tables, including controlled dated fixtures in a separate database for windows/retention/zero/missing data. Label synthetic time explicitly.
6. Save architecture report with scenario table, full column inventory, evidence, defects, gaps and unverified cases. Update ignored local handoffs. Preserve unrelated files, stop owned processes only; no publication.

## Evidence and handoff

Evidence: ignored `output/metrics-e2e-acceptance/` and `output/playwright/metrics-e2e-acceptance/`; report `docs/architecture/2026-10-18-metrics-e2e-acceptance.md`. Synthetic credentials remain private and are omitted from public evidence. Main acceptance uses a controlled AI boundary, proving application/accounting plumbing rather than live-model quality. Acceptance owner: this chat; product fixes require separate work.
