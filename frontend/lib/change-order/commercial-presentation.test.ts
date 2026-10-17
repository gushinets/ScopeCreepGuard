import { readFileSync } from 'node:fs'
import { expect, it } from 'vitest'
import { commercialPresentation, createChangeOrderDocument, buildChangeOrderText, type EditableDraft } from './document'

const fixture = JSON.parse(readFileSync('../ci/contracts/commercial-presentation.json', 'utf8'))

for (const locale of fixture.languages) {
  for (const rationale of fixture.rationales) {
    it(`projects ${locale.language}/${rationale.name} paid/free/paid without mutating source`, () => {
      const source: EditableDraft = { ...fixture.source, language: locale.language, rationale: rationale.value,
        aiValues: rationale.name === 'AI' ? { rationale: rationale.value } : undefined }
      const snapshot = JSON.stringify(source)
      const paid = createChangeOrderDocument(source)
      expect(paid.commercialTerms.map(row => row.value)).toEqual([locale.effort, fixture.paidFee])
      expect(paid.additionalItems.some(row => row.value === rationale.value)).toBe(!!rationale.value)
      const free = { ...source, noAdditionalCharge: true }
      expect(commercialPresentation(free)).toEqual(fixture.freeProjection)
      const rendered = createChangeOrderDocument(free)
      expect(rendered.commercialTerms.map(row => row.value)).toEqual([locale.effort, locale.freeFee])
      expect(rendered.additionalItems.some(row => row.label === rendered.labels.rationale)).toBe(false)
      expect(rendered.scheduleImpact).toBe(source.timelineImpact)
      const copy = buildChangeOrderText(free)
      for (const untouched of [source.description, source.note, source.additionalTerms]) expect(copy).toContain(untouched)
      expect(rendered.additionalItems.some(row => row.label === rendered.labels.endDate)).toBe(true)
      // The persistence format retains the checkbox and paid source fields on reload.
      const restored = JSON.parse(JSON.stringify(free)) as EditableDraft
      expect(restored).toEqual(free)
      expect(createChangeOrderDocument(restored)).toEqual(rendered)
      expect(createChangeOrderDocument({ ...restored, noAdditionalCharge: false })).toEqual(paid)
      expect(JSON.stringify(source)).toBe(snapshot)
    })
  }
}
