import { expect, it } from 'vitest'
import { documentFixture } from '@/features/drafts/model/fixtures'
import { invalidAiEstimate } from './invalid-estimate'

const order = { ...documentFixture.changeOrder!, estimatedHours: '0.00', additionalCost: '0.00', aiValues: { estimatedHours: '0', additionalCost: '0', currency: 'USD' } }
it('offers refresh for existing zero AI proposals even when commercial terms are current', () => {
  expect(invalidAiEstimate(order, true)).toBe(true)
  expect(invalidAiEstimate(order, false)).toBe(false)
})
it('preserves deliberate free work and manually entered terms', () => {
  expect(invalidAiEstimate({ ...order, noAdditionalCharge: true }, true)).toBe(false)
  expect(invalidAiEstimate({ ...order, aiValues: { ...order.aiValues, manualPrice: 'true' } }, true)).toBe(false)
  expect(invalidAiEstimate({ ...order, estimatedHours: '2', additionalCost: '60' }, true)).toBe(false)
})
