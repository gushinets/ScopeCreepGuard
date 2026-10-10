import { readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, it } from 'vitest'
import { buildAnalysisMessages, buildRegenerationMessages } from '@/tests/generation-baseline/prompt'
import { ANALYSIS_JSON_SCHEMA } from '@/tests/generation-baseline/analysis-json-schema'
import { buildClientMaterialMessages, CLIENT_MATERIALS_SCHEMA } from '@/tests/generation-baseline/client-materials'
import { analysisFixture, documentFixture, projectSnapshotFixture } from '@/lib/drafts/fixtures'
import { parseAnalysisResult } from '@/lib/llm/schema'
import { supportedClientLanguage, normalizeLanguageTag } from '@/lib/client-language'
import { commercialSignature } from '@/lib/change-order/commercial-signature'

it('retains Intl rejection and Unicode extension canonicalization review vectors', () => {
  for (const tag of ['no-bok', 'abcd', 'en-abc-abc', 'en-a-foo-a-bar', 'en-t-en-us-h0', 'en-t-en-abc-abc']) {
    expect(normalizeLanguageTag(tag)).toBeUndefined()
    expect(supportedClientLanguage(tag)).toBeUndefined()
  }
  expect(normalizeLanguageTag('en-u-ca-gregory-ca-buddhist')).toBe('en-u-ca-gregory')
  for (const [raw, canonical] of [
    ['en-u-ca-yes', 'en-u-ca'], ['en-u-ms-imperial', 'en-u-ms-uksystem'],
    ['en-u-tz-usnavajo', 'en-u-tz-usden'], ['uk-SU-u-ca-gregory', 'uk-UA-u-ca-gregory'],
    ['en-t-en-us-h0-hybrid', 'en-t-en-us-h0-hybrid'],
  ]) expect(normalizeLanguageTag(raw)).toBe(canonical)
})

it('freezes exact generation messages, schemas and runtime normalization before cutover', () => {
  const inputs = ['en', 'ru'].flatMap(locale => ['en', 'ru', 'es', 'de', 'pt-BR', 'es-419', undefined].flatMap(documentLanguage => ['hourly', 'fixed'].map(pricingModel => ({
    scope: 'Five pages only. Русский текст.', request: 'Add page 😀 / Añadir página.', industry: 'Development', locale,
    startDate: '2026-01-01', endDate: pricingModel === 'hourly' ? '2026-12-01' : undefined,
    pricingModel, currency: 'EUR', hourlyRate: pricingModel === 'hourly' ? '100.00' : null,
    fixedPrice: pricingModel === 'fixed' ? '5000.00' : null, draftCreatedAt: '2026-10-10T09:00:00.000Z', documentLanguage,
  }))))
  const cases = inputs.map(input => ({ input, messages: buildAnalysisMessages(input as Parameters<typeof buildAnalysisMessages>[0]),
    replies: ['warm', 'neutral', 'firm'].map(tone => ({ tone, messages: buildRegenerationMessages({ ...input, tone, previousReply: 'Old reply 😀' } as Parameters<typeof buildRegenerationMessages>[0]) })),
  }))
  const languages = ['en', 'es-419', 'PT-br', 'de', 'ar', 'JA-jp', 'zh-hant-TW', 'iw', 'in-ID', 'mo-MD', 'uk-SU', 'et-810', 'en-Latn-US', 'ru-Latn', 'en_US', 'und']
    .map(raw => ({ raw, broad: normalizeLanguageTag(raw) ?? null, supported: supportedClientLanguage(raw) ?? null }))
  const fixture = { cases, languages, analysisSchema: ANALYSIS_JSON_SCHEMA, materialsSchema: CLIENT_MATERIALS_SCHEMA,
    materials: buildClientMaterialMessages({ locale: 'ru', clientLanguage: 'de', scope: 'Five pages.', request: 'Add page', analysis: analysisFixture }),
    normalized: parseAnalysisResult(analysisFixture, 'en'), analysisFixture, documentFixture, projectSnapshotFixture,
    signature: commercialSignature(projectSnapshotFixture, '2026-12-01'),
  }
  const file = resolve('../contracts/compatibility/any-640/generation.json')
  if (process.env.SCG_FREEZE_GENERATION === '1') writeFileSync(file, JSON.stringify(fixture, null, 2) + '\n')
  expect(JSON.parse(JSON.stringify(fixture))).toEqual(JSON.parse(readFileSync(file, 'utf8')))
})
