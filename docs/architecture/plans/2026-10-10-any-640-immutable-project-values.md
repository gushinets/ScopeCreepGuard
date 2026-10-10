# ANY-640 — Slice C immutable project values

Goal: remove shallow project immutability without changing product behavior.
Architecture: nested frozen/slotted values inside domain/application; mutable
JSON exists only in HTTP conversion and local database conversion.
Stack: Python 3.12, dataclasses, FastAPI, SQLAlchemy/PostgreSQL; existing Next gateway.
Spec: the user's architectural correction and the existing ANY-640 Slice C plan.

Branch: `codex/any-640-fastapi-business-workflows`; current HEAD:
`0249a0bed2d1d182e9580031195ed70e0d22d12e`; exact ANY-639 parent:
`97518baacaba56a1a2542fe145b14d62644c5fda`.
The user authorizes this correction in the current checkout. Preserve existing
Slice C and unrelated changes; no branch operations, staging, commit or push.

Scope: eliminate mutable project-card dictionaries from domain/application
inputs, stored state and outputs. Preserve HTTP/OpenAPI, auth/error precedence,
full PATCH omission/null behavior, transactions, history ordering and deletion.
No migration/schema change, frontend business change or Slice D work.

- [x] Add failing regression tests for parser/repository/application mutation;
   add serializer aliasing regression coverage.
   Use frozen, slotted dataclasses in `modules/projects/domain.py`: agreed scope,
   lexical project date, optional client (supplied versus omitted), pricing,
   project dates/card, project entity, history entry and project detail. Nested
   fields are immutable scalar/enum/value objects; collections are tuples.
- [x] Move request parsing to `api/project_input.py`. Temporary decoded JSON is
   validated using unchanged rules and converted to a typed card before calling
   use cases. PATCH passes an async typed-card reader, invoked only after the
   owned project lookup. Keep lexical dates to preserve year-zero compatibility.
- [x] Change repository ports/adapters and use cases to accept/return immutable
   values. Database conversion dictionaries stay adapter-local. History returns
   immutable entries in a tuple, with project IDs for grouping. Use cases return
   immutable project details/tuples; HTTP routes alone assemble response JSON.
   Serializers allocate fresh nested JSON on every call and expose no aliases.
- [x] Verify mutation rejection, repository/use-case isolation, all frozen parser
   vectors and unchanged HTTP corpus. Run backend unit/API/disposable PostgreSQL,
   frontend tests/contracts, Ruff/mypy/TypeScript, OpenAPI/types and diff checks.
   Record exact results below and in the verification document; update ignored
   `AGENT.md`. Stop for review, with Slice D still pending.

Compatibility decisions: wire names, nullable legacy commercial terms, optional
lastChecked/draftId, two-decimal prices and omitted client updates remain exact.
Frozen dataclasses enforce ordinary Python immutability; deliberately bypassing
it with object.__setattr__ is outside the supported domain interface.

Verification: 181 backend tests passed in 72.37s; 386 frontend tests/45 files and
19 Python contract tests passed; frozen 21-operation HTTP corpus unchanged.
Ruff/format (89 files), mypy (38 sources), TypeScript, frontend lint and
OpenAPI/generated-type freshness passed. Exact commands/results and changed
files are recorded in the architectural correction section of
`../any-640-verification.md`. No staging, commit, push or migration change.
Follow-up ownership: Slice C review; generation/proofs remain TypeScript until
separately approved Slice D. Inherited Vite/two lint warnings remain; full browser
form journeys are still Slice G. The inherited CommercialTerms helper is retained.

Subsequent publication authorization: the user approved committing/pushing this
completed correction with Slice C to the existing child branch. Final staged
checks are recorded in the verification document; Slice D remains unapproved.
