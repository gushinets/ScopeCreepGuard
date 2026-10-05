import { PDFDocument, type PDFFont, type PDFPage, rgb } from 'pdf-lib'
import fontkit from '@pdf-lib/fontkit'
import { createChangeOrderDocument, type EditableDraft } from './document'

const PAGE_WIDTH = 595
const PAGE_HEIGHT = 842
const MARGIN = 48
const CONTENT_WIDTH = PAGE_WIDTH - MARGIN * 2
const NAVY = rgb(0.055, 0.09, 0.16)
const INK = rgb(0.11, 0.15, 0.22)
const MUTED = rgb(0.38, 0.43, 0.5)
const LINE = rgb(0.82, 0.84, 0.87)
const PAPER = rgb(0.965, 0.97, 0.98)
const ACCENT = rgb(0.93, 0.59, 0.12)
const WHITE = rgb(1, 1, 1)

function safeText(value: string): string {
  return value.replace(/[—–‑]/g, '-').replace(/\r/g, '')
}

function wrapText(text: string, font: PDFFont, size: number, maxWidth: number): string[] {
  const lines: string[] = []
  for (const paragraph of safeText(text).split('\n')) {
    if (!paragraph.trim()) { lines.push(''); continue }
    let current = ''
    for (const word of paragraph.split(/\s+/)) {
      const next = current ? `${current} ${word}` : word
      if (font.widthOfTextAtSize(next, size) <= maxWidth) { current = next; continue }
      if (current) lines.push(current)
      current = ''
      let fragment = ''
      for (const character of Array.from(word)) {
        if (fragment && font.widthOfTextAtSize(fragment + character, size) > maxWidth) { lines.push(fragment); fragment = '' }
        fragment += character
      }
      current = fragment
    }
    if (current) lines.push(current)
  }
  return lines
}

export async function createChangeOrderPdf(draft: EditableDraft, regularFontBytes: Uint8Array, boldFontBytes: Uint8Array): Promise<Uint8Array> {
  const document = createChangeOrderDocument(draft)
  const pdf = await PDFDocument.create()
  pdf.registerFontkit(fontkit)
  // fontkit's variable-font subsetter corrupts Cyrillic glyph positioning.
  const regular = await pdf.embedFont(regularFontBytes, { subset: false })
  const bold = await pdf.embedFont(boldFontBytes, { subset: false })
  let page!: PDFPage
  let y = 0

  const addPage = (first = false) => {
    page = pdf.addPage([PAGE_WIDTH, PAGE_HEIGHT])
    if (first) {
      page.drawRectangle({ x: 0, y: PAGE_HEIGHT - 118, width: PAGE_WIDTH, height: 118, color: NAVY })
      page.drawRectangle({ x: 0, y: PAGE_HEIGHT - 122, width: PAGE_WIDTH, height: 4, color: ACCENT })
      page.drawRectangle({ x: MARGIN, y: PAGE_HEIGHT - 42, width: 78, height: 19, color: ACCENT })
      page.drawText(safeText(document.status), { x: MARGIN + 9, y: PAGE_HEIGHT - 36, font: bold, size: 8.5, color: NAVY })
      const titleLines = wrapText(document.title, bold, 21, 350).slice(0, 2)
      titleLines.forEach((line, index) => page.drawText(line, { x: MARGIN, y: PAGE_HEIGHT - 72 - index * 25, font: bold, size: 21, color: WHITE }))
      const rightX = 420
      page.drawText(safeText(document.labels.documentNumber), { x: rightX, y: PAGE_HEIGHT - 54, font: bold, size: 7.5, color: rgb(0.68, 0.72, 0.78) })
      page.drawText(safeText(document.reference), { x: rightX, y: PAGE_HEIGHT - 68, font: regular, size: 8.5, color: WHITE })
      page.drawText(safeText(document.labels.created), { x: rightX, y: PAGE_HEIGHT - 89, font: bold, size: 7.5, color: rgb(0.68, 0.72, 0.78) })
      for (const [index, line] of wrapText(document.createdDate, regular, 8.5, 125).entries()) page.drawText(line, { x: rightX, y: PAGE_HEIGHT - 103 - index * 11, font: regular, size: 8.5, color: WHITE })
      y = PAGE_HEIGHT - 145
    } else {
      page.drawText(safeText(document.title), { x: MARGIN, y: PAGE_HEIGHT - 35, font: bold, size: 9, color: NAVY })
      page.drawText(safeText(document.reference), { x: PAGE_WIDTH - MARGIN - bold.widthOfTextAtSize(document.reference, 8), y: PAGE_HEIGHT - 35, font: bold, size: 8, color: MUTED })
      page.drawLine({ start: { x: MARGIN, y: PAGE_HEIGHT - 44 }, end: { x: PAGE_WIDTH - MARGIN, y: PAGE_HEIGHT - 44 }, thickness: 1, color: LINE })
      y = PAGE_HEIGHT - 68
    }
  }

  const ensureSpace = (height: number) => { if (y - height < 58) addPage(false) }
  const paragraph = (text: string, options: { font?: PDFFont; size?: number; color?: ReturnType<typeof rgb>; indent?: number; after?: number } = {}) => {
    const activeFont = options.font ?? regular
    const size = options.size ?? 10.5
    const lineHeight = size * 1.36
    const indent = options.indent ?? 0
    for (const line of wrapText(text, activeFont, size, CONTENT_WIDTH - indent)) {
      ensureSpace(lineHeight)
      if (line) page.drawText(line, { x: MARGIN + indent, y, font: activeFont, size, color: options.color ?? INK })
      y -= lineHeight
    }
    y -= options.after ?? 3
  }
  const sectionHeading = (heading: string) => {
    ensureSpace(27)
    y -= 5
    page.drawRectangle({ x: MARGIN, y: y - 3, width: 4, height: 18, color: ACCENT })
    page.drawText(safeText(heading).toUpperCase(), { x: MARGIN + 13, y, font: bold, size: 10.5, color: NAVY })
    y -= 20
  }

  addPage(true)

  const metadataHeight = 16 + document.metadata.length * 19
  ensureSpace(metadataHeight)
  page.drawRectangle({ x: MARGIN, y: y - metadataHeight + 8, width: CONTENT_WIDTH, height: metadataHeight, color: PAPER, borderColor: LINE, borderWidth: 0.8 })
  y -= 10
  for (const item of document.metadata) {
    page.drawText(safeText(item.label).toUpperCase(), { x: MARGIN + 14, y, font: bold, size: 7.5, color: MUTED })
    const valueLines = wrapText(item.value, regular, 9.5, CONTENT_WIDTH - 150)
    page.drawText(valueLines[0] ?? '', { x: MARGIN + 132, y: y - 1, font: regular, size: 9.5, color: INK })
    y -= 19
  }
  y -= 7
  paragraph(document.introduction, { color: MUTED, after: 5 })

  sectionHeading(document.sections[0].heading)
  if (document.description) paragraph(document.description, { after: 4 })

  sectionHeading(document.sections[1].heading)
  for (const [index, item] of document.commercialTerms.entries()) {
    const valueSize = index === document.commercialTerms.length - 1 ? 12 : 10.5
    const valueLines = wrapText(item.value, bold, valueSize, 220)
    const rowHeight = Math.max(31, 18 + valueLines.length * (valueSize * 1.2))
    ensureSpace(rowHeight + 3)
    const rowY = y - rowHeight + 6
    page.drawRectangle({ x: MARGIN, y: rowY, width: CONTENT_WIDTH, height: rowHeight, color: index % 2 === 0 ? PAPER : WHITE, borderColor: LINE, borderWidth: 0.7 })
    page.drawText(safeText(item.label), { x: MARGIN + 13, y: y - 7, font: bold, size: 9, color: MUTED })
    valueLines.forEach((line, lineIndex) => page.drawText(line, { x: PAGE_WIDTH - MARGIN - 13 - bold.widthOfTextAtSize(line, valueSize), y: y - 8 - lineIndex * valueSize * 1.2, font: bold, size: valueSize, color: NAVY }))
    y -= rowHeight
  }
  y -= 4

  sectionHeading(document.sections[2].heading)
  if (document.scheduleImpact) paragraph(document.scheduleImpact, { after: 4 })

  sectionHeading(document.sections[3].heading)
  for (const item of document.additionalItems) {
    paragraph(item.label.toUpperCase(), { font: bold, size: 7.5, color: MUTED, after: 0 })
    paragraph(item.value, { after: 2 })
  }

  ensureSpace(90)
  sectionHeading(document.approvalHeading)
  const approvalColumns = [
    { label: document.labels.approvedBy, value: document.approval.approverName },
    { label: document.labels.date, value: document.approval.approvalDate },
  ]
  const columnGap = 24
  const columnWidth = (CONTENT_WIDTH - columnGap) / 2
  const approvalTop = y
  for (const [index, entry] of approvalColumns.entries()) {
    const x = MARGIN + index * (columnWidth + columnGap)
    page.drawText(safeText(entry.label).toUpperCase(), { x, y: approvalTop, font: bold, size: 7.5, color: MUTED })
    const valueLines = wrapText(entry.value, regular, 9.5, columnWidth).slice(0, 2)
    valueLines.forEach((line, lineIndex) => page.drawText(line, { x, y: approvalTop - 17 - lineIndex * 12, font: regular, size: 9.5, color: INK }))
    page.drawLine({ start: { x, y: approvalTop - 43 }, end: { x: x + columnWidth, y: approvalTop - 43 }, thickness: 0.7, color: MUTED })
  }
  y = approvalTop - 53

  const pages = pdf.getPages()
  pages.forEach((pdfPage, index) => {
    pdfPage.drawLine({ start: { x: MARGIN, y: 39 }, end: { x: PAGE_WIDTH - MARGIN, y: 39 }, thickness: 0.7, color: LINE })
    pdfPage.drawText(safeText(document.labels.draftFooter).toUpperCase(), { x: MARGIN, y: 24, font: bold, size: 6.8, color: MUTED })
    const pageText = `${document.labels.page} ${index + 1} / ${pages.length}`
    pdfPage.drawText(safeText(pageText), { x: PAGE_WIDTH - MARGIN - regular.widthOfTextAtSize(safeText(pageText), 7), y: 24, font: regular, size: 7, color: MUTED })
  })

  return pdf.save()
}
