# ANY-702 / ANY-703: documentation alignment

- Base: origin/main, 7e836ea; branch: codex/any-702-703-documentation-alignment.
- Workflow: existing local checkout; unrelated changes preserved. User authorized documentation fix and publication to main.
- Scope: reconcile review comments from Mikhail dated 2026-10-20; no runtime, schema, migrations or UI changes.

## Steps and evidence

1. Compared workflow/profile/LLM constraints in migrations 0002, 0003, 0005 and 0006, History deduplication in workflow repository, and T1/T2 UoW sequencing.
2. Corrected retention to indefinite archival; marked seven-day purge as historical, not implemented.
3. Corrected History cardinality to original automatic snapshot plus explicit edited-material archives; preserved immutable originals, read-only viewing and explicit Reopen.
4. Corrected stage_key/physical_index uniqueness and distinguished DB constraints from LLM service checks. Marked proposed tables/API as future design.
5. Verified diff whitespace and documentation assertions. Runtime tests unnecessary: documentation only.

## Limitations and ownership

This records schema/code review, not new browser acceptance. Historical UI evolution and future tables remain explicitly proposals. No purge/restoration functionality or manual-save UI is added. Repeat acceptance belongs to the ANY-702/703 reviewer.
