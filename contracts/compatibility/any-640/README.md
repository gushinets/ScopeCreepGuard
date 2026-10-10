# ANY-640 compatibility gate

`http.json` is frozen from the real TypeScript route handlers and Drizzle queries
on an owned disposable PostgreSQL 17 database. Only current-user/locale resolution
and external LLM adapters are replaced with synthetic deterministic inputs.
Actual registration/login, bcrypt, session issuance, draft proof issuance and
verification, parsers, serialization, transactions and cascading deletes run.
This is handler-level characterization, not production HTTP/E2E evidence.

Slices B/C now check four auth and five project operations through real Next.js forwarding
handlers and an owned FastAPI HTTP server against the same disposable database.
Only still-TypeScript workflows use the synthetic current-user resolver; Python
authentication and project authorization verify cookies and load owners themselves. The original HTTP baseline remains
unchanged. `auth.json` adds synthetic bcryptjs and JOSE vectors; Python-generated
hashes/tokens are checked back in Node, including Unicode, lone surrogates, nulls
and the bcrypt 72-byte boundary. Session tokens issued by either runtime include
integer `iat`/`exp`, an HS256 header, UUID subject and email. Python rejects signed
tokens missing those issued-format claims; it accepts future `iat` as JOSE does.

`projects.json` freezes 19 actual TypeScript parser cases, including validation
order, JavaScript whitespace, omitted/null clients, ignored browser fields,
calendar dates and Number/toFixed monetary behavior. Python unit tests replay
these vectors. The corpus now exercises nine Python operations and twelve TS
operations; legacy history creation and all generation/draft writes remain TS.

UUID/token aliases are consistent symbolic identifiers, not real credentials.
UTC time is fixed. Cookies remain individual strings; JSONL remains exact bytes.
Persistence deltas and logical LLM call counts are checked independently before
comparison. The corpus covers each of the 21 methods, unauthenticated protected
operations and invalid null bodies. Per-slice gates add their own edge/failure
and frontend-consumption evidence; this corpus does not replace those tests.

```text
node scripts/verify-any640.mjs --suite contracts
```

Only an intentional reviewed baseline change uses `--update-fixtures`. Never
point `SCG_COMPATIBILITY_DATABASE_URL` at an application database. The root runner
creates and owns the database, disables application integration variables, and
removes only its verified container/databases. The TypeScript test refuses
targets outside the harness's loopback/user/database convention.

Approved migration exceptions: supplied foreign Origins reject with 403 and
errors.requestFailed; otherwise unmapped failures normalize to JSON 500 with
errors.requestFailed; concurrent duplicate registration maps to 409.
No business operation moves to Python in slice A. OpenAPI continues describing
implemented routes only, not hypothetical business handlers.
