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
})
