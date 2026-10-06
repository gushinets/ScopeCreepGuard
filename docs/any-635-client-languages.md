# ANY-635 client-language follow-up repairs

Work remains on `codex/any-635-client-material-languages`. No branch switch, commit, push or PR was made. Unrelated existing tracked and untracked changes were preserved.

## Design

Language selection calls the dedicated `POST /api/client-materials/language` endpoint. It validates a supported BCP 47 override, authenticates the user, verifies project ownership and the matching history entry, validates the original analysis context, and rate limits generation.

Its model flow translates existing replies and applicable Change Order text instead of classifying scope or estimating commercial terms. The output schema contains only clientLanguage, replies, nullable Change Order text and document labels. It cannot return a verdict, confidence, reasoning, citations, additional-work flag, effort, price or currency. Parsing and application explicitly pick replacement fields so even unexpected model values cannot replace established analysis or commercial estimates. The displayed analysis stays in the interface locale. Canonical RU/EN/ES document labels remain in use; other supported languages use supplied complete labels.

The estimate endpoint again unconditionally requires complete commercial terms, genuine additional work, a valid estimate and matching currency, including when documentLanguage is supplied. Language changes never call it. Explicit estimate refreshes preserve the existing analysis and replies; stale responses cannot replace a newer result.

## Persistence

Versioned local snapshots use `scg:client-materials:<user>:<project>:<history>` with a user-bound active-result pointer. They contain original analysis context and separate translated AI materials. On reload, restoration checks the authenticated user's project/history, request, scope/commercial context and interface locale before showing the saved result and explicit language choice. Old history with no snapshot remains safe; legacy draft normalization is retained.

A language change also updates any saved draft even when its editor is closed. Existing comparison against previous AI values updates only untouched generated text, preserving manual edits, deletions, numeric amounts, currency, identities, approval and additional terms. Same-language regeneration refreshes the visible editor and replies. Storage failure produces localized feedback rather than falsely promising restoration.

## Truthful PDF support

The selector and manual-language API input boundaries accept an explicit supported set of 26 languages using Latin, Cyrillic or Greek script, with regional variants and compatible explicit script subtags. Unsupported languages, script overrides and locale extensions are rejected before generation with accessible localized feedback. UI locales remain RU/EN.

PDF export checks the language and verifies every document character against both bundled Noto Sans fonts. Unsupported scripts or missing glyphs, including those introduced through manual edits or client names, fail explicitly before a PDF is saved. The UI reports the failure in its interface locale. Preview, Copy and PDF continue sharing the document builder and current draft values.

Supported primary languages: ru, en, es, de, fr, it, nl, pl, pt, tr, uk, bg, el, cs, sk, hr, ro, hu, fi, sv, da, nb, et, lv, lt, id. Examples of accepted regional tags: pt-BR, en-US, de-DE. Arabic, Hebrew, Japanese, Chinese, Thai and other languages outside the set are deliberately unsupported by this exporter.

## Final verification

All requested commands completed with exit code 0:

| Command | Result |
| --- | --- |
| `vitest run` | 29 test files, 225 tests passed |
| `tsc --noEmit` | Passed |
| `eslint .` | 0 errors; 2 pre-existing unused-variable warnings in openai.test.ts and schema.test.ts |

The commands ran through `pnpm exec` with `PNPM_CONFIG_VERIFY_DEPS_BEFORE_RUN=false`, using the installed dependencies without changing the existing pnpm-workspace configuration.

Coverage includes dedicated endpoint use, immutable displayed analysis and numeric estimates, full provider reload restoration, repeated overrides with preserved edited drafts, legacy compatibility, estimate guards with and without overrides, Ukrainian Cyrillic PDF text (including ґ/є/і/ї), unsupported script/glyph rejection, localized UI feedback, and existing RU/EN/ES/DE document flows.

## Remaining limits

PDF support is intentionally limited to the listed languages/scripts. Mixed unsupported-script names, emoji or unsupported glyphs must be corrected before export; the exporter reports an explicit error rather than producing missing glyphs. No new font files or complex-script shaping stack were added.

Translation quality and faithful wording still depend on the model; no live model call was made during verification. User-edited draft text is preserved and is not automatically translated. Restoration depends on browser local storage; unavailable storage is reported. Snapshots with changed scope/commercial context or a different interface locale are not restored, avoiding stale analysis.

## Changed files in this follow-up

- `app/api/change-orders/estimate/route.test.ts`
- `app/api/change-orders/estimate/route.ts`
- `app/api/client-materials/language/route.test.ts`
- `app/api/client-materials/language/route.ts`
- `components/scope-guard/change-order.test.tsx`
- `components/scope-guard/change-order.tsx`
- `components/scope-guard/client-language.test.tsx`
- `components/scope-guard/result-panel.tsx`
- `components/scope-guard/store.tsx`
- `docs/any-635-client-languages.md`
- `lib/api/errors.ts`
- `lib/change-order/pdf.test.ts`
- `lib/change-order/pdf.ts`
- `lib/client-language.test.ts`
- `lib/client-language.ts`
- `lib/client-material-storage.test.ts`
- `lib/client-material-storage.ts`
- `lib/client-materials.ts`
- `lib/llm/analyze-request.ts`
- `lib/llm/client-materials.test.ts`
- `lib/llm/client-materials.ts`
- `lib/llm/regenerate-request.ts`
- `messages/en.json`
- `messages/ru.json`
