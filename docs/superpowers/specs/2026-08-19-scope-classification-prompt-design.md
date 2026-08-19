# Design: Scope Classification Prompt + GPT-5.4 nano

Date: 2026-08-19  
Source: product owner prompt rewrite; existing analyze path in `lib/llm/`  
Slice: Replace classification rules and model call; keep the current result contract and UI

## Goal

Replace how Scope Creep Guard classifies a client request as in-scope, borderline, or out-of-scope. Use the new evidence-based classification prompt, call OpenAI `gpt-5.4-nano` with reasoning, and still return the existing `AnalysisResult` JSON so the result panel, three reply tones, Change Order, confidence, citations, and history stay unchanged.

## Decisions (locked)

| Topic | Choice |
|---|---|
| Product surface | Keep current UI and `AnalysisResult` (confidence, citations, suggestion, `replies.warm/neutral/firm`, `changeOrder`) |
| LLM calls | One Responses API call per Check scope |
| Model | `gpt-5.4-nano` |
| Reasoning | On: `reasoning.effort = "medium"` (nano default is `none`; do not leave default) |
| Structured output | Existing strict JSON schema `scope_analysis` via Responses `text.format` |
| Conversation context | Omit from v1 (no UI field, no empty section in the user prompt) |
| Project type | Existing project `industry`: `Development`, `Design`, or `Marketing` |
| Verdict JSON values | `in_scope` / `borderline` / `out_of_scope` (same meanings as IN_SCOPE / OUT_OF_SCOPE / BORDERLINE) |
| Locale | Generated text in UI locale (English or Russian); citations not translated |
| Fallback / retries | None. Fail fast on missing key, API error, incomplete response, or invalid JSON |
| Out of this slice | UI redesign, conversation-context field, new JSON fields, DB migration, showing reasoning tokens, Chat Completions |

## Architecture

Keep Next.js App Router + Postgres + session cookies. The Check scope path stays:

1. User selects a project and enters a client request.
2. Client `POST /api/analyze` with `{ projectId, request }`.
3. API verifies session, loads the project owned by the current user.
4. Server builds system + user strings in `lib/llm/prompt.ts`.
5. Server calls OpenAI Responses API from `lib/llm/openai.ts`.
6. Server parses `output_text` with the existing `parseAnalysisResult`.
7. Client renders the existing result UI and writes history as today.

### OpenAI call

Replace `client.chat.completions.create` (`gpt-4o-mini`) with:

- `client.responses.create`
- `model: "gpt-5.4-nano"`
- `reasoning: { effort: "medium" }`
- `instructions`: system prompt string
- `input`: user prompt string
- `text.format`: `{ type: "json_schema", name: "scope_analysis", strict: true, schema: ANALYSIS_JSON_SCHEMA }`
- Read `response.output_text` (not `choices[0].message.content`)

Reasoning tokens stay internal. Do not display chain-of-thought.

`buildAnalysisMessages` still returns `{ role, content }[]` for tests and for mapping into `instructions` / `input`: index 0 is system, index 1 is user.

## Prompt

Fully replace `lib/llm/prompt.ts`. Drop the old classification procedure, “listed capability / add the ability” rules, and few-shot examples (CE backends, extra pages, newsletter).

### System prompt — classification (verbatim)

```
You are Scope Creep Guard.

Your task is to determine whether a new client request is covered by the agreed project scope.

You must be neutral and evidence-based.

Do NOT classify a request as in-scope merely because it is related to the project.

Use only the supplied Project Scope and Client Request as the primary evidence.

CLASSIFICATION:

IN_SCOPE:
The requested work is explicitly included in the agreed scope, OR it is reasonably necessary to complete or correct an explicitly agreed deliverable.

OUT_OF_SCOPE:
The request introduces a new deliverable, functionality, integration, platform, channel, audience, work category, or additional quantity beyond an explicit scope limit.

BORDERLINE:
The scope is ambiguous, broad, missing an important limitation, or supports both interpretations.

ANALYSIS PROCESS:

1. Identify what the client is actually asking the freelancer to do.
2. Find the closest relevant part of the agreed scope.
3. Compare the requested work with that scope.
4. Check whether the request changes:
   - deliverables
   - functionality
   - quantity
   - revisions
   - integrations
   - platforms/channels
   - project phase
5. Determine whether the request is necessary to complete an existing deliverable or represents additional value/work.
6. Classify the request.

IMPORTANT RULES:

- Never invent terms that are not present in the scope.
- Never assume common industry practices are included unless the scope supports that interpretation.
- If important information is missing, classify as BORDERLINE rather than guessing.
- A bug or defect in an agreed deliverable is normally IN_SCOPE unless the scope explicitly says otherwise.
- A new feature or improvement is not a bug merely because it improves an existing deliverable.
- Small effort does not mean in-scope.
- Large effort does not mean out-of-scope.
- Classification is based on contractual scope, not estimated effort.
```

Do not put “Return structured JSON only.” here. It belongs after the output appendix so the schema rules are not cut off.

### System prompt — output appendix

Append after the classification text. This appendix exists only to fill the current schema; it must not weaken the classification rules. End the full system prompt with `Return structured JSON only.`

Required mappings:

| Concept from the new spec | Existing field |
|---|---|
| IN_SCOPE / OUT_OF_SCOPE / BORDERLINE | `verdict`: `in_scope` / `out_of_scope` / `borderline` |
| One-sentence what the client is asking | `summary` |
| Comparison plus narrative scope reference | `reasoning` |
| Closest agreed-scope evidence | `citations`: 0–3 verbatim phrases from the scope, not paraphrases, not translated |
| Scope gap + recommended action | `suggestion` (empty string when there is no gap and no extra action) |
| Client reply | `replies.warm`, `replies.neutral`, `replies.firm` |
| Change Order draft | `changeOrder` (always filled; same in-scope rules as today) |
| Certainty | `confidence`: integer 0–100, never a 0–1 fraction |

Output-appendix rules:

- JSON keys and verdict enum values stay English and lowercase (`in_scope`, `borderline`, `out_of_scope`).
- Write `summary`, `reasoning`, `suggestion`, `replies.*`, and `changeOrder` in the UI locale language (English or Russian), even if the scope or request is in another language.
- `replies.warm` / `neutral` / `firm` are professional client-facing replies the freelancer can send.
- `summary`, `reasoning`, `replies.*`, and all `changeOrder` fields must be non-empty for every verdict, including `in_scope`. `suggestion` may be empty.
- Fill `changeOrder` in all verdicts. For `in_scope`: `description` names the included work, `timelineImpact` is none / no extra time, `additionalCost` is included / $0, `note` remains the draft disclaimer (not legal advice), still in the output language.
- Citations must support this verdict. For `in_scope`, cite the matching included clause. Never cite an unrelated exclusion.
- Never invent scope clauses that are not in the provided scope.

### User prompt

```
PROJECT TYPE:
{{industry}}

AGREED PROJECT SCOPE:
{{scope}}

NEW CLIENT REQUEST:
{{request}}
```

Do not include `OPTIONAL CONVERSATION CONTEXT`.

## Components

| Module | Change |
|---|---|
| `lib/llm/prompt.ts` | Replace system and user messages as specified |
| `lib/llm/openai.ts` | Responses API, `gpt-5.4-nano`, `reasoning.effort = medium`, read `output_text` |
| `lib/llm/prompt.test.ts` | Assert new classification rules, user-prompt labels, output appendix, locale; assert old rules are absent |
| `lib/llm/analysis-json-schema.ts` | No change |
| `lib/llm/schema.ts` | No change |
| `app/api/analyze/route.ts` | No contract change |
| Result UI, DB, history | No change |

```
[Check Scope]
  request + projectId → POST /api/analyze
    → session user
    → project WHERE id AND user_id
    → Responses API (gpt-5.4-nano, reasoning medium, json_schema)
    → parseAnalysisResult
  → result panel
  → POST .../history (existing)
```

## Error handling

Pre-OpenAI behavior unchanged: `401` unauthenticated, `404` foreign/missing project, `400` empty request/scope or oversized input, `429` rate limit, invalid locale is a server invariant.

| Situation | Behavior |
|---|---|
| Missing `OPENAI_API_KEY` | Log `openai_api_key_missing`; client `errors.analysisUnavailable` (`503`) |
| OpenAI API error / timeout | Log `openai_request_failed`; client `errors.analysisFailed` (`502`) |
| Response `status` not `completed` (including incomplete from output/reasoning limits) | Log `openai_incomplete` with `status` and `incomplete_details.reason`; same `502` |
| Empty `output_text` | Log `openai_empty_content`; same `502` |
| JSON parse failure | Log `openai_json_parse_failed`; same `502` |
| Schema/parser rejection | Log `openai_analysis_shape_invalid` with keys; same `502` |

On OpenAI failures, log event plus `status`, `incomplete_details.reason` when present, and token usage (`input`, `output`, `reasoning`) when the API returns them. Do not log scope or the client request.

No retries. No keyword heuristic. No invented defaults for missing fields.

## Testing

Unit (`lib/llm/prompt.test.ts`):

- System prompt contains the new classification definitions, 6-step process, bug-vs-feature rule, effort ≠ scope, and “never invent terms”.
- System prompt contains the output appendix (lowercase verdicts, three tones, Change Order, confidence 0–100, locale language, verbatim citations).
- Russian locale instructs Russian generated fields; English locale instructs English.
- User prompt contains `PROJECT TYPE`, `AGREED PROJECT SCOPE`, `NEW CLIENT REQUEST`, and the supplied industry/scope/request.
- User prompt does not contain conversation context.
- Old prompt fragments are absent: listed-capability / “add the ability”, CE/backends few-shot, extra-pages few-shot, newsletter few-shot.

Unchanged: `schema.test.ts`, rate-limit tests, file-upload tests.

Live smoke (manual, `OPENAI_API_KEY` required): Check scope on the Acme examples for in / borderline / out; confirm verdict, three replies, Change Order, and a history row. Missing key still shows `errors.analysisUnavailable`.

Regression: `pnpm test`, `pnpm lint`, `pnpm exec tsc --noEmit`.

## Done when

A user can Check scope and get a verdict produced by the new classification rules on `gpt-5.4-nano` with medium reasoning, still rendered in the existing result UI (confidence, citations, suggestion, three tones, Change Order), with history saved, and with the same fail-fast errors when the key is missing or the model output is invalid.

## Explicit non-goals (this slice)

- Conversation-context UI or prompt section
- New result JSON fields (`scope_reference`, `scope_gap`, `recommended_action`, single `client_reply`)
- Changing verdict storage from lowercase enums
- Redesigning the result panel
- Two-step LLM (classify then draft replies)
- Displaying reasoning / chain-of-thought
- Hidden retries or keyword fallback
- Chrome Extension, billing, DOCX, voice learning
