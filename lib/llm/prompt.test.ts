import { describe, expect, it } from 'vitest'
import { buildAnalysisMessages } from './prompt'

const input = {
  scope: 'Build a landing page.',
  request: 'Add a blog.',
  industry: 'Development' as const,
}

describe('buildAnalysisMessages', () => {
  it('instructs the model to write generated fields in Russian when locale is ru', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'ru' })

    expect(system.content).toContain('Russian')
    expect(system.content).not.toContain('professional English')
    expect(system.content).toMatch(/summary|reasoning|replies|changeOrder/i)
  })

  it('instructs the model to write generated fields in English when locale is en', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(system.content).toContain('English')
    expect(system.content).toMatch(/summary|reasoning|replies|changeOrder/i)
  })

  it('keeps citations as verbatim scope phrases regardless of locale', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'ru' })

    expect(system.content.toLowerCase()).toMatch(/verbatim|do not translate/)
  })

  it('compares request meaning rather than surface verbs like add', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(system.content).toMatch(/meaning/i)
    expect(system.content).toMatch(/surface wording/i)
  })

  it('treats a listed capability as in_scope even when the request says add the ability', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(system.content).toMatch(/listed capability/i)
    expect(system.content).toMatch(/add the ability/i)
    expect(system.content).toMatch(/in_scope/)
  })

  it('forbids citing exclusions that are not about the same request subject', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(system.content).toMatch(/same subject/i)
    expect(system.content).toMatch(/unrelated exclusion/i)
  })

  it('includes compact few-shot examples for listed capability, extra quantity, and adjacent work', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(system.content).toMatch(/product backends/i)
    expect(system.content).toMatch(/3 more pages/i)
    expect(system.content).toMatch(/newsletter/i)
  })

  it('requires non-empty changeOrder fields for every verdict including in_scope', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(system.content).toMatch(/non-empty/i)
    expect(system.content).toMatch(/every verdict/i)
    expect(system.content).toMatch(/in_scope/)
    expect(system.content).toMatch(/changeOrder/)
  })
})
