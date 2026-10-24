# Full user journeys

This boundary is reserved for browser journeys spanning application components.
No new browser framework or fabricated passing smoke test is added by ANY-638.

Verify on a disposable database: register/login; protected pages; create/edit a
project; analyze and regenerate replies; switch interface and client languages
independently; save/reopen/edit drafts after reload; keep historical terms after
project edits; export Change Order PDF; label/export evaluations; delete a
project; logout. Check EN/RU UI, foreign-resource isolation and missing drafts.

Current deterministic coverage remains colocated in frontend. Live model checks
are separately invoked and require credentials; CI uses deterministic doubles.

## ANY-556 Draft acceptance

`any556-browser.js` and `any556-save-failure.js` are Playwright CLI `run-code`
journeys, not a new application test framework. Run them only against the
documented disposable full stack with synthetic accounts and private object
storage. The collection journey expects 53 owned active Drafts: projects
`ANY-556 Catalog` (created 2026-10-19), `ANY-556 Website` (created at midnight UTC
2026-10-20), one Draft at 2026-10-21 midnight, and 50 more on 2026-10-20 including
equal creation timestamps. Archived and foreign projects stay outside that count.
Begin authenticated in EN on the Draft screen. Downloads/screenshots go to the
ignored `output/playwright/any556/` directory.

```text
npx --yes --package @playwright/cli playwright-cli -s=any556 open http://YOUR-DISPOSABLE-APP
# Register a synthetic account, create the two named projects, and prepare fixtures.
npx --yes --package @playwright/cli playwright-cli -s=any556 run-code --filename tests/e2e/any556-browser.js
npx --yes --package @playwright/cli playwright-cli -s=any556 run-code --filename tests/e2e/any556-save-failure.js
```

The second journey intercepts only the test browser's Draft PUT, checks that no
CSV GET/download starts after failure, removes the interception, uses existing
Retry, and downloads the confirmed revision. It makes no analysis call. Controlled
analysis-dependent CSV fields use repository fixtures rather than paid providers.
Exact revisions, image IDs, results, query plans and limitations are in the
[ANY-556 report](../../docs/architecture/2026-10-24-any-556-draft-csv-verification.md).
