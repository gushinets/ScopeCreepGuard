# Draft filtering and CSV

ANY-556 implements the current **Draft** workflow. The historical issue's History
wording does not apply. Export reads neither create History entries nor finalize
agreements. Projects, existing language selection, and automatic saving retain
their existing behavior.

## Collection

The Draft heading contains Filter and Export. Filters select an owned active
project, inclusive creation-date range, and creation order. Default: all active
projects, newest first. Modified dates do not affect sorting. Equal creation
timestamps use Draft ID in the same direction as the timestamp.

Dates are displayed with seconds and UTC labels. Date-only API bounds mean
midnight UTC through, but excluding, midnight after the last day. The maximum
upper date is 9999-12-30; 9999-12-31 cannot form a representable next-day bound.

The collection uses 50-row pages, with a maximum API page size of 100. Export
includes **every matching saved Draft**, independently of the current page.
No matches exports headers only. Empty accounts, no matches, and loading failures
have separate states. Filtering preserves unrelated URL parameters, fragments,
and navigation state. Older responses cannot replace newer filter results.

## API

| GET route | Query parameters |
| --- | --- |
| `/api/v2/drafts` | `projectId`, `createdFrom`, `createdTo`, `sort=newest\|oldest`, `limit=50` (1–100), `offset=0` |
| `/api/v2/drafts/export.csv` | Same project/date/sort parameters; `locale=en\|ru` (default en); no pagination |
| `/api/v2/drafts/{identifier}/export.csv` | `locale=en\|ru`; optional positive revision string `expectedRevision` |

The collection returns `drafts`, matching `total`, and owner-scoped `hasDrafts`
ignoring filters. Each summary includes Draft/project IDs, current project name,
request preview, nullable verdict, and creation/modification timestamps.

Invalid dates, reversed ranges, UUIDs, sort, and pagination yield the established
400 invalid-request response. Foreign/nonexistent/archived project filters all
produce no matches; individual exports return the same 404 for inaccessible or
missing Drafts. A supplied revision mismatch returns 409. Export responses are
`text/csv; charset=utf-8`, attachment filenames containing only constants and
validated identifiers, and `Cache-Control: private, no-store`. Error responses on
Draft read paths are private too.

## Exporting an open Draft

The workspace heading offers CSV even without analysis or an agreement. Export
first flushes existing autosave and waits for confirmed persistence. The CSV GET
contains that confirmed revision. Failed saves retain edits and existing Retry
feedback; no stale download starts. Unresolved recovery blocks export.

Switching Drafts, navigating away, or editing while the CSV request is pending
cancels the download. A competing server revision also prevents download. Retry
after saving/reviewing the current state. CSV reads do not change revisions,
timestamps, analysis, History, project/session state, or business metrics.

## CSV schema

One header and one row per current Draft, in this fixed order for both endpoints.
RU headers below correspond to the EN schema. Verdict and boolean values are
localized; client text is preserved in its saved language. Language and currency
remain canonical codes. Missing fields stay blank, including the payment flag
when there is no agreement document.

| EN header | RU header | Saved value |
| --- | --- | --- |
| Draft ID | ID черновика | Draft ID |
| Project ID | ID проекта | Current Draft project ID |
| Project name | Название проекта | Current project name |
| Draft created at (UTC) | Черновик создан (UTC) | Existing creation timestamp |
| Draft updated at (UTC) | Черновик изменён (UTC) | Existing modification timestamp |
| Draft revision | Ревизия черновика | Exact revision string |
| Current client request | Текущий запрос клиента | `requestText` |
| Analysis verdict | Результат анализа | Current linked analysis verdict |
| Analysis explanation | Объяснение анализа | Current linked analysis `reasoning` |
| Analysis is stale | Анализ устарел | Saved `analysisIsStale` |
| Selected client reply | Выбранный ответ клиенту | Edited `draftDocument.reply.text` |
| Client-material language | Язык материалов для клиента | `draftDocument.reply.language` |
| Additional-work description | Описание дополнительных работ | Current change-order `description` |
| Estimated hours | Оценка часов | Current `estimatedHours` decimal string |
| Additional amount | Сумма за дополнительные работы | Current `additionalCost` decimal string |
| Currency | Валюта | Current change-order `currency` |
| Without additional payment | Без дополнительной оплаты | Explicit `noAdditionalCharge` |
| Schedule change | Изменение сроков | Current `timelineImpact` |

EN booleans: Yes/No; RU: Да/Нет. Verdicts: In scope / Borderline / Out of scope;
Входит в объём работ / Спорный случай / Выходит за рамки работ. No analysis values
or commercial terms are inferred from prose, preliminary estimates, or defaults.

Python's CSV library writes CRLF records with a UTF-8 BOM. EN uses commas; RU uses
semicolons. Quoting preserves delimiters, quotes, multiline text, and Unicode.
Amounts/hours stay exact saved decimal strings: `2.50` remains `2.50`, without a
binary floating-point conversion or rounding. Timestamps have explicit `Z` UTC.

### Spreadsheet formula protection

For each string cell, inspect characters after leading Unicode whitespace and
characters in Unicode categories Cc/Cf. If the first significant character is
`=`, `+`, `-`, or `@`, prepend one ASCII apostrophe to the **entire original cell**.
Keep the original whitespace, control characters, and text after the apostrophe.
For example, `\t=SUM(1,2)` becomes `'\t=SUM(1,2)`. Ordinary text is unchanged.
Quoting alone does not disable spreadsheet formulas. The prefix intentionally
changes hazardous cell text; importing it as raw text preserves that prefix.

## Limits and schema decision

List and export are independent current-state reads, not a frozen snapshot
across requests. Concurrent creation/archive may shift offset page boundaries.
CSV currently materializes matching rows in memory; no queue, truncation, or
background job is introduced. Exports contain only the documented flat fields,
without internal snapshots, credentials, or provider telemetry.

No schema migration is required: existing non-null `timestamptz` columns and the
one-Draft-per-project constraint are reused. Owner listing/project/Draft indexes
already exist. Representative query-plan evidence and actual verification
limitations are recorded in the ANY-556 verification report.
