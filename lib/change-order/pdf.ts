import { PDFDocument, rgb } from 'pdf-lib'
import fontkit from '@pdf-lib/fontkit'
import { buildChangeOrderText, type EditableDraft } from './document'

export async function createChangeOrderPdf(draft: EditableDraft, fontBytes: Uint8Array): Promise<Uint8Array> {
  const pdf = await PDFDocument.create()
  pdf.registerFontkit(fontkit)
  const font = await pdf.embedFont(fontBytes, { subset: true })
  const width = 595, height = 842, margin = 48, bodySize = 11, lineHeight = 17
  let page = pdf.addPage([width, height])
  let y = height - margin
  const drawLine = (line: string, size = bodySize) => {
    if (y < margin + lineHeight) { page = pdf.addPage([width, height]); y = height - margin }
    page.drawText(line, { x: margin, y, font, size, color: rgb(0.15, 0.17, 0.2) })
    y -= size === 16 ? 30 : lineHeight
  }
  const wrap = (line: string, size: number) => {
    let current = ''
    for (const word of line.split(/\s+/)) {
      if (!word) continue
      const next = current ? `${current} ${word}` : word
      if (font.widthOfTextAtSize(next, size) <= width - margin * 2) { current = next; continue }
      if (current) drawLine(current, size)
      current = ''
      for (const character of Array.from(word)) {
        if (font.widthOfTextAtSize(current + character, size) > width - margin * 2 && current) { drawLine(current, size); current = '' }
        current += character
      }
    }
    if (current) drawLine(current, size)
  }
  const lines = buildChangeOrderText(draft).split('\n')
  wrap(lines[0], 16)
  const date = lines[1]
  page.drawText(date, { x: width - margin - font.widthOfTextAtSize(date, bodySize), y, font, size: bodySize })
  y -= 32
  for (const line of lines.slice(3)) {
    if (!line) { y -= 8; continue }
    wrap(line, bodySize)
  }
  return pdf.save()
}
