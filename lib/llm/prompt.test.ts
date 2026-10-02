import { describe, expect, it } from 'vitest'
import { buildAnalysisMessages } from './prompt'

const input = {
  scope: 'Build a landing page.',
  request: 'Add a blog.',
  industry: 'Development' as const,
  locale: 'en' as const,
}

describe('buildAnalysisMessages', () => {
  it.each([
    ['ru', 'Russian'],
    ['en', 'English'],
  ] as const)(
    'uses %s as the interface language while keeping replies and Change Order request-language specific',
    (locale, language) => {
      const [system] = buildAnalysisMessages({ ...input, locale })

      expect(system.content).toContain(`Application interface language: ${language}.`)
      expect(system.content).toMatch(/Write summary, reasoning, and suggestion in the application interface language/i)
      expect(system.content).toMatch(/Determine the language of NEW CLIENT REQUEST/i)
      expect(system.content).toMatch(/all client-facing replies and every Change Order field in the language of NEW CLIENT REQUEST/i)
      expect(system.content).not.toMatch(/summary, reasoning, and suggestion in the language of NEW CLIENT REQUEST/i)
    },
  )

  it('keeps an English client reply separate from a Russian interface', () => {
    const [system, user] = buildAnalysisMessages({
      ...input,
      locale: 'ru',
      request: 'Add a new column for customer.',
    })

    expect(system.content).toContain('Application interface language: Russian.')
    expect(user.content).toContain('Add a new column for customer.')
    expect(system.content).toMatch(
      /MUST be written exclusively in the language of NEW CLIENT REQUEST/i,
    )
    expect(system.content).toMatch(
      /Do not write client-facing replies or Change Order fields in the application interface language when it differs from NEW CLIENT REQUEST/i,
    )
  })

  it('falls back to the interface language for a language-neutral client request', () => {
    const [system] = buildAnalysisMessages({
      ...input,
      locale: 'ru',
      request: 'SEO',
    })

    expect(system.content).toMatch(
      /If NEW CLIENT REQUEST has no detectable language.*use the application interface language for client-facing replies and every Change Order field/i,
    )
  })

  it('keeps citations as verbatim scope phrases regardless of request language', () => {
    const [system] = buildAnalysisMessages(input)

    expect(system.content.toLowerCase()).toMatch(/verbatim/)
    expect(system.content.toLowerCase()).toMatch(/do not translate/)
  })

  it('uses the evidence-based classification definitions and process', () => {
    const [system] = buildAnalysisMessages(input)

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
    const [system] = buildAnalysisMessages(input)

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
    const [system] = buildAnalysisMessages(input)

    expect(system.content).toMatch(/non-empty/i)
    expect(system.content).toMatch(/every verdict/i)
    expect(system.content).toMatch(/in_scope/)
    expect(system.content).toMatch(/changeOrder/)
  })

  it('builds the labeled user prompt without conversation context', () => {
    const [, user] = buildAnalysisMessages(input)

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
    const [system] = buildAnalysisMessages(input)

    expect(system.content).not.toMatch(/listed capability/i)
    expect(system.content).not.toMatch(/add the ability/i)
    expect(system.content).not.toMatch(/product backends/i)
    expect(system.content).not.toMatch(/3 more pages/i)
    expect(system.content).not.toMatch(/newsletter/i)
    expect(system.content).not.toMatch(/surface wording/i)
  })
})
