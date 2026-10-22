# Positive additional-work estimates

Branch `codex/design-onboarding`; earlier changes retained, no push/PR.

The active structured-output runner accepted zero effort/cost for additional paid work. The older validation function was not called by that runner; a test that only exercised it would miss the failure. Added a focused shared positive-estimate check to both the legacy validator and the live structured runner's composition path, including cached candidates. With complete paid commercial terms and additional work, zero effort or cost now produces correction feedback through the existing bounded retry flow. Pricing formulas, model, manual agreement contents and deliberate free-work choices are unchanged.

Existing agreements with zero AI proposals now expose Update estimate even when their commercial signature is current. No automatic rewriting of saved user documents. Manual/free terms remain protected by the existing merge flow.

Docker verification: build/typecheck passed; frontend lint/boundaries passed (100 modules); 33 focused frontend tests passed (proposal recovery/manual/free terms and persistent editor regressions); 76 Python tests passed (positive estimates, language validation and structured correction regressions); targeted Ruff and git diff check passed.

Browser verification in English and Russian used the real isolated Docker API/PostgreSQL and controlled provider. Restored an archived synthetic project via History, configured the test fixture's hourly terms to 30 USD, opened Drafts, entered a new request, checked it, and prepared an agreement. The controlled provider deliberately returned zero hours/cost on its first analysis attempt. The active runner rejected it and obtained the corrected 8-hour/240-USD result; the form and reload retained those values. Captured screenshots were visually inspected. Existing-zero recovery is covered by focused frontend tests; user documents were not modified for verification. No paid calls. Full backend CI was not run.

- [Russian agreement](restored-estimate-ru.png)
- [English agreement](restored-estimate-en.png)

`browser-verification.js` records the journey using the synthetic accounts from previous verification. It runs against port 3100 and rearchives those test projects afterwards. Normal port 3000 serves the updated frontend and its real worker remains on gpt-6-luna. No API/schema migration was required.
