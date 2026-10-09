# ANY-639 execution evidence — 2026-10-09

Branch: codex/any-639-data-contracts-and-alembic, based on ANY-638 commit
9d317c391254ae06424c195536ab94e437d9cb3c.

Completed checks:

- Frontend with harness-owned disposable PostgreSQL: 40 files, 369 tests passed,
  no skips. An earlier database-free run passed 346 with 23 expected skips.
- Frontend lint: zero errors, two existing unused-variable warnings. Route type
  generation, TypeScript check and production build succeeded. Existing Next.js
  middleware convention deprecation remains.
- Backend initial complete integration run: 52 passed. Expanded run: 63 passed.
  Real Drizzle replay, Alembic empty upgrade and ORM catalog parity passed;
  populated adoption preserves every business row and old migration ledger.
- Independent reviewer found URL query-target override and draft request trimming
  defects; regressions reproduced six failures, then all eight tests passed after
  fixes. Draft-list UTC milliseconds were also corrected.
- Generated OpenAPI check passed. All three Compose configurations validated.
  Backend image built successfully with baseline assets included in its build.

Final verification:

- The outage regression exposed Psycopg cancellation cleanup extending a request
  to 13 seconds. Readiness now returns within its deadline while lifespan owns
  cleanup. Final full PostgreSQL run: 63 passed in 42.98 seconds, including outage
  deadline/recovery, failed-commit rollback, commercial checks and cascades.
- Ruff check and formatting check passed; 56 Python files already formatted.
  Generated OpenAPI check passed. Final image build and all Compose configs passed.
- Final image runtime verified liveness and PostgreSQL readiness plus installed
  baseline manifest/Alembic assets, using a newly owned disposable database.
- GitHub CI also runs on the ANY-639 branch and accepts a stacked PR against
  codex/any-638-frontend-backend-foundation, preserving the intended dependency.
- Independent final review found no remaining Critical or Important defects;
  reviewer independently ran 30 focused regression/contract/lifecycle/health tests.
- A temporary review-service credit limit interrupted verification earlier; the
  final checks and reviewer recheck resumed successfully after it cleared.

ANY-639 implementation tests used only owned ephemeral, volume-free PostgreSQL.
Later, the user requested local startup and reported a broken workspace. Its
existing local database was behind migrations 0004–0006. Applying those existing
Drizzle migrations preserved one user, two projects and 29 history entries; the
authenticated workspace API then returned 200. This was local runtime setup,
not Alembic adoption or production migration. The app was stopped on request.
No production database was mutated. Drizzle remains
migration owner; no business routes or event tables were added. The future
audit/analytics decision remains open for a separate approved task.

Execution adaptations: native PowerShell ledger replaces shell tracking helpers;
the user's approved local checkout was used; disposable harness setup moved
forward to prove ORM behavior; Windows uses an explicit selector loop factory;
invalid database configuration keeps liveness available and readiness unavailable.

## PR #14 review fixes

Both reported findings reproduced before changes: inherited PGPORT reached
engine construction for both mutation operations; noncanonical supported tags
were rejected. Mutation commands now reject inherited PGPORT before connecting,
including with an explicit URL port. Client materials canonicalize casing and
registered aliases before the existing supported-language/script restrictions.
Langcodes 3.5.1 is locked without language-data extras; explicit script subtags
remain. A bounded SU/810/172 successor mapping matches frontend Intl behavior.

Final complete backend run: 88 passed in 49.24 seconds, including disposable
PostgreSQL. Ruff, formatting and OpenAPI checks passed. Final production image
built and passed contract import/canonicalization assertions. Independent review
found no remaining Important issues and compared 315 supported tag combinations
with Node Intl without differences. No frontend code or application database
changed in this follow-up.

## Linux CI provenance correction

PR CI exposed one failure with 87 passing tests: provenance recorded raw Windows
CRLF bytes while GitHub read LF bytes. Verified the normalized digest for 0000
equals both its Git blob and the reported Linux hash. Generator and source check
now share CRLF-to-LF normalization and record that format explicitly. Regenerated
manifest changes only provenance hashes/metadata; schema definitions remain
identical. Drizzle migration files and its raw-byte ledger hashes remain untouched.

Three regression tests cover CRLF/LF equivalence, changed SQL rejection and lone
CR preservation. Final full disposable-PostgreSQL run: 91 passed in 49.61 seconds;
Ruff/format checks passed. Independent review passed and separately verified four
focused provenance tests.
