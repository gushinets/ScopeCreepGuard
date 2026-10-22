# Prevent zero estimates for additional work

- Branch/base: current `codex/design-onboarding`; preserve all existing changes, no push/PR.
- Inspect the restored-project/new-request journey and commercial estimate validation. Do not change selected model, pricing formulas, manually edited terms or historical documents.
- Steps: reproduce zero additional-work estimates; reject invalid zero AI proposals through existing correction flow; expose estimate refresh for existing invalid AI proposals while preserving deliberate free/manual work; add focused tests; verify Docker and browser with controlled responses.
- No migrations or data rewriting. Implemented and verified: Docker build/typecheck/lint, 76 Python and 33 frontend tests, and Russian/English browser restore → Drafts → new check → agreement journeys, including an intentionally zero first AI response corrected by the live runner. See [evidence and screenshots](../evidence/2026-10-22-positive-additional-work-estimates/README.md) for details/limitations. No API/schema changes, no push/PR. Owner: current task.
