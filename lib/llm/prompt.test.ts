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

    expect(system.content.toLowerCase()).toMatch(/verbatim/)
    expect(system.content.toLowerCase()).toMatch(/do not translate/)
  })

  it('uses the evidence-based classification definitions and process', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(system.content).toContain('You are Scope Creep Guard.')
    expect(system.content).toMatch(/Do NOT classify a request as in-scope merely because it is related/i)
    expect(system.content).toContain('IN_SCOPE:')
    expect(system.content).toContain('OUT_OF_SCOPE:')
    expect(system.content).toContain('BORDERLINE:')
    expect(system.content).toMatch(/reasonably necessary to complete or correct/i)
    expect(system.content).toMatch(/Identify what the client is actually asking/i)
    expect(system.content).toMatch(/platforms\/channels/)
    expect(system.content).toMatch(/Never invent terms that are not present in the scope/i)
    expect(system.content).toMatch(/bug or defect in an agreed deliverable is normally IN_SCOPE/i)
    expect(system.content).toMatch(/new feature or improvement is not a bug/i)
    expect(system.content).toMatch(/Small effort does not mean in-scope/i)
    expect(system.content).toMatch(/Classification is based on contractual scope, not estimated effort/i)
  })

  it('maps classification labels onto lowercase verdict enums in the output appendix', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(system.content).toContain('in_scope')
    expect(system.content).toContain('out_of_scope')
    expect(system.content).toContain('borderline')
    expect(system.content).toMatch(/replies\.warm/)
    expect(system.content).toMatch(/replies\.neutral/)
    expect(system.content).toMatch(/replies\.firm/)
    expect(system.content).toMatch(/confidence is an integer from 0 to 100/i)
    expect(system.content.trim().endsWith('Return structured JSON only.')).toBe(
      true,
    )
  })

  it('requires non-empty changeOrder fields for every verdict including in_scope', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(system.content).toMatch(/non-empty/i)
    expect(system.content).toMatch(/every verdict/i)
    expect(system.content).toMatch(/in_scope/)
    expect(system.content).toMatch(/changeOrder/)
  })

  it('builds the labeled user prompt without conversation context', () => {
    const [, user] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(user.content).toContain('PROJECT TYPE:')
    expect(user.content).toContain('Development')
    expect(user.content).toContain('AGREED PROJECT SCOPE:')
    expect(user.content).toContain('Build a landing page.')
    expect(user.content).toContain('NEW CLIENT REQUEST:')
    expect(user.content).toContain('Add a blog.')
    expect(user.content).not.toMatch(/CONVERSATION CONTEXT/i)
    expect(user.content).not.toMatch(/^PROJECT SCOPE:/m)
    expect(user.content).not.toMatch(/^CLIENT REQUEST:/m)
  })

  it('drops the old listed-capability procedure and few-shot examples', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(system.content).not.toMatch(/listed capability/i)
    expect(system.content).not.toMatch(/add the ability/i)
    expect(system.content).not.toMatch(/product backends/i)
    expect(system.content).not.toMatch(/3 more pages/i)
    expect(system.content).not.toMatch(/newsletter/i)
    expect(system.content).not.toMatch(/surface wording/i)
  })
})
