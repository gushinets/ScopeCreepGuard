// @vitest-environment jsdom
import { cleanup, render, screen, within } from '@testing-library/react'
import { IntlProvider } from 'use-intl'
import { afterEach, expect, it } from 'vitest'
import en from '@/shared/i18n/messages/en.json'
import ru from '@/shared/i18n/messages/ru.json'
import { analysisFixture } from '@/features/drafts/model/fixtures'
import { applyClientMaterials } from '@/features/analysis/model/client-materials'
import type { AnalysisResult } from '@/shared/api/models'
import { ScopeAssessment } from '@/features/analysis/scope-assessment'

afterEach(cleanup)
const analysis = { ...analysisFixture, changeOrder: null, estimate: { estimatedHours: 8, additionalCost: '240', currency: 'USD' as const } }

it.each(['en', 'ru'] as const)('shows complete assessment with %s labels and interface-language analysis', locale => {
  const messages = locale === 'ru' ? ru : en
  const result = locale === 'ru' ? { ...analysis, summary: 'Новая страница', reasoning: 'Новая страница не включена в согласованный объём.', suggestion: 'Согласуйте дополнительные работы.' } : analysis
  render(<IntlProvider locale={locale} messages={messages}><ScopeAssessment result={result} request="build a new page for our custmores" /></IntlProvider>)
  for (const text of [result.summary, result.reasoning, result.citations[0], result.suggestion!, messages.result.clientRequest, messages.result.whyHeading, messages.result.nextStep, messages.result.preliminaryEstimate, messages.changeOrder.hoursLabel, messages.changeOrder.costLabel]) expect(screen.getByText(text)).toBeTruthy()
  expect(screen.getByText('build a new page for our custmores')).toBeTruthy()
  expect(screen.getByText('8')).toBeTruthy()
  expect(screen.getByText((_, element) => element?.tagName === 'DD' && element.textContent === new Intl.NumberFormat(locale, { style: 'currency', currency: 'USD' }).format(240))).toBeTruthy()
  expect(screen.getByText(/90/)).toBeTruthy()
})

it('translation preserves assessment and its preliminary estimate', () => {
  const before = structuredClone(analysis)
  const translated = applyClientMaterials(analysis, { clientLanguage: 'es', replies: { warm: 'Hola', neutral: 'Hola', firm: 'Hola' }, changeOrder: null })
  const view = render(<IntlProvider locale="en" messages={en}><ScopeAssessment result={translated} /></IntlProvider>)
  expect(screen.getByText(analysis.reasoning)).toBeTruthy()
  expect(screen.getByText('$240.00')).toBeTruthy()
  expect(screen.queryByText('Hola')).toBeNull()
  expect(analysis).toEqual(before)
  view.unmount()
  render(<IntlProvider locale="en" messages={en}><ScopeAssessment result={JSON.parse(JSON.stringify(translated))} /></IntlProvider>)
  expect(screen.getByText(analysis.reasoning)).toBeTruthy()
  expect(screen.getByText('$240.00')).toBeTruthy()
})

it('reads historical estimate fields without rendering client-language document prose', () => {
  render(<IntlProvider locale="en" messages={en}><ScopeAssessment result={analysisFixture} /></IntlProvider>)
  expect(screen.getByText('€200.00')).toBeTruthy()
  expect(screen.queryByText('Two days')).toBeNull()
  expect(screen.queryByText('Draft')).toBeNull()
})

it('renders a known numeric zero estimate while leaving an unknown amount absent', () => {
  const view = render(<IntlProvider locale="en" messages={en}><ScopeAssessment result={{ ...analysis, estimate: { estimatedHours: 0, additionalCost: '0', currency: 'USD' } }} /></IntlProvider>)
  expect(screen.getByText('$0.00')).toBeTruthy()
  view.unmount()
  render(<IntlProvider locale="en" messages={en}><ScopeAssessment result={{ ...analysis, estimate: { estimatedHours: 0, additionalCost: '', currency: 'USD' } }} /></IntlProvider>)
  expect(screen.queryByText('$0.00')).toBeNull()
})

it.each(['in_scope', 'borderline', 'out_of_scope'] as const)('tolerates missing optional fields for %s', verdict => {
  const result: AnalysisResult = { ...analysisFixture, verdict, citations: [], suggestion: undefined, estimate: undefined, changeOrder: null, hasAdditionalWork: undefined }
  render(<IntlProvider locale="en" messages={en}><ScopeAssessment result={result} /></IntlProvider>)
  expect(screen.getByText(result.reasoning)).toBeTruthy()
  expect(screen.queryByText(en.result.fromScope)).toBeNull()
  expect(within(screen.getByRole('region')).queryByText(en.changeOrder.hoursLabel)).toBeNull()
})
