openapi.json is generated from FastAPI, never manually authored. From backend run uv run python scripts/export_openapi.py --output ../contracts/openapi.json; use --check with the same path to verify freshness. All 24 public API operations are implemented by Python; Next.js handlers only forward them.

ANY-641 migration matrix:

| Operation | Python responsibility | Frontend responsibility |
|---|---|---|
| GET /api/drafts/{draftId}/pdf | Owned saved document and historical snapshot; read-only PDF | Download saved unchanged editor |
| POST /api/change-orders/pdf | Validate owned project/optional historical draft; render submitted edits without persistence | Submit unsaved or changed editor; no implicit save |
| POST /api/scope/extract | Authenticated bounded temporary TXT/Markdown/PDF extraction and structured warnings | Upload/cancel, localized feedback, editable result before save |

Currency selection preserves entered amounts; there is no conversion endpoint or rate provider.

OpenAPI is generated from apps/api scope_guard_api.main.create_app. Synchronize
the root uv workspace first; generation imports the app without running startup
migrations. Architecture relocation must preserve contract/type equality.
