export type Box = { left: number; top: number; right: number; bottom: number; width: number; height: number }
export type Point = { left: number; top: number }
const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(value, max))

export function placeGuide(target: Box, size: { width: number; height: number }, viewport: { width: number; height: number }, obstacles: Box[]): Point | null {
  const { width, height } = size
  const top = clamp(target.top + target.height / 2 - height / 2, 16, viewport.height - height - 16)
  const left = clamp(target.left, 16, viewport.width - width - 16)
  const candidates = [
    { left: target.right + 36, top },
    { left: target.right + 36, top: clamp(target.top, 16, viewport.height - height - 16) },
    { left: target.left - width - 36, top },
    { left: target.left - width - 36, top: clamp(target.top, 16, viewport.height - height - 16) },
    { left, top: target.bottom + 24 },
    { left, top: target.top - height - 24 },
  ]
  return candidates.find(candidate => candidate.left >= 16 && candidate.left + width <= viewport.width - 16 && candidate.top >= 16 && candidate.top + height <= viewport.height - 16 && !obstacles.some(box => candidate.left < box.right + 6 && candidate.left + width > box.left - 6 && candidate.top < box.bottom + 6 && candidate.top + height > box.top - 6)) ?? null
}

export function guideConnector(target: Box, card: Box) {
  let x1: number, y1: number, x2: number, y2: number, path: string
  if (card.left >= target.right || card.right <= target.left) {
    const right = card.left >= target.right
    x1 = right ? target.right + 4 : target.left - 4
    y1 = target.top + target.height / 2
    x2 = right ? card.left : card.right
    y2 = card.top + Math.min(56, card.height / 2)
    const middle = (x1 + x2) / 2
    path = `M ${x1} ${y1} C ${middle} ${y1}, ${middle} ${y2}, ${x2} ${y2}`
  } else {
    const below = card.top >= target.bottom
    x1 = clamp(target.left + Math.min(target.width / 2, 60), card.left + 20, card.right - 20)
    x2 = x1
    y1 = below ? target.bottom + 4 : target.top - 4
    y2 = below ? card.top : card.bottom
    const middle = (y1 + y2) / 2
    path = `M ${x1} ${y1} C ${x1} ${middle}, ${x2} ${middle}, ${x2} ${y2}`
  }
  return { path, x: x1, y: y1 }
}
