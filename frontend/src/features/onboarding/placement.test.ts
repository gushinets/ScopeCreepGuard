import { expect, it } from 'vitest'
import { guideConnector, placeGuide, type Box } from './placement'

const target: Box = { left: 300, right: 500, top: 300, bottom: 344, width: 200, height: 44 }
const size = { width: 304, height: 206 }
const viewport = { width: 1440, height: 900 }

it('keeps the card within the viewport and away from occupied controls', () => {
  const blocker = { left: 520, right: 1000, top: 300, bottom: 600, width: 480, height: 300 }
  const position = placeGuide(target, size, viewport, [blocker])
  expect(position).not.toBeNull()
  expect(position!.left).toBeGreaterThanOrEqual(16)
  expect(position!.left + size.width).toBeLessThanOrEqual(viewport.width - 16)
  expect(position!.top).toBeLessThan(target.top - size.height)
})

it('uses the inline destination when no clear floating position exists', () => {
  expect(placeGuide(target, size, viewport, [{ left: 0, top: 0, right: 1440, bottom: 900, width: 1440, height: 900 }])).toBeNull()
})

it('connects the control edge to the card without drawing across the control', () => {
  const card = { left: 536, right: 840, top: 219, bottom: 425, width: 304, height: 206 }
  const line = guideConnector(target, card)
  expect(line.x).toBeGreaterThan(target.right)
  expect(line.y).toBe(target.top + target.height / 2)
  expect(line.path).toContain('536 275')
  expect(line.path).not.toContain('NaN')
})
