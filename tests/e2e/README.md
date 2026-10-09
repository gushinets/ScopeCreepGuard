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
