// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import type { EditableDraft } from '@/lib/change-order/document'
import { ChangeOrder } from './change-order'
import { germanLabels } from '@/lib/change-order/german-fixture'

const pdfMock = vi.hoisted(() => vi.fn())
vi.mock('@/lib/change-order/pdf', () => ({ createChangeOrderPdf: pdfMock }))
vi.mock('next-intl', () => ({ useLocale: () => 'en', useTranslations: () => (key: string) => key }))

const original: EditableDraft = {
  createdAt: '2026-10-05T12:00:00Z', language: 'en', projectName: 'Website', description: 'Add blog',
  estimatedHours: '10', additionalCost: '1000', currency: 'USD', timelineImpact: 'Two days',
  rationale: 'Extra work', note: '', clientName: '', clientEmail: '', endDate: '',
  additionalTerms: '', providerName: '', clientApproverName: '', approvalDate: '', noAdditionalCharge: false,
}

beforeEach(() => {
  localStorage.clear()
  pdfMock.mockResolvedValue(new Uint8Array([37, 80, 68, 70, 45]))
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, arrayBuffer: async () => new ArrayBuffer(8) }))
  Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:pdf') })
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() })
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: vi.fn().mockResolvedValue(undefined) } })
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
})
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); vi.clearAllMocks() })

it('retains supplied German labels in preview, copied content, export and storage', async () => {
  render(<ChangeOrder initialDraft={{ ...original, language: 'de', changeOrderLabels: germanLabels, description: 'Zusätzliche Änderungen' }} projectName="Website" projectId="p1" historyId="h1" userId="u1" />)
  const preview = screen.getByTestId('change-order-document-preview')
  expect(preview.textContent).toContain('ÄNDERUNGSAUFTRAG')
  expect(preview.textContent).toContain('Geschätzter Aufwand')
  expect(preview.textContent).not.toContain('hours')
  fireEvent.change(document.querySelector('#co-description')!, { target: { value: 'Geänderte Größe' } })
  fireEvent.click(screen.getByRole('button', { name: 'copy' }))
  await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith(expect.stringContaining('ÄNDERUNGSAUFTRAG — ENTWURF')))
  expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Geänderte Größe')
  fireEvent.click(screen.getByRole('button', { name: 'downloadPdf' }))
  await waitFor(() => expect(pdfMock).toHaveBeenCalledWith(expect.objectContaining({ language: 'de', changeOrderLabels: germanLabels, description: 'Geänderte Größe' }), expect.any(Uint8Array), expect.any(Uint8Array)))
  expect(JSON.parse(localStorage.getItem('scg:change-order:u1:p1:h1')!).changeOrderLabels).toEqual(germanLabels)
})

it('copies and exports the current edited draft', async () => {
  render(<ChangeOrder initialDraft={original} projectName="Website" projectId="p1" historyId="h1" userId="u1" />)
  fireEvent.change(document.querySelector('#co-description')!, { target: { value: 'Add three posts' } })
  fireEvent.change(document.querySelector('#co-additionalCost')!, { target: { value: '850' } })
  fireEvent.click(screen.getByRole('button', { name: 'copy' }))
  await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith(expect.stringContaining('850 USD')))
  expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Add three posts')
  fireEvent.click(screen.getByRole('button', { name: 'downloadPdf' }))
  await waitFor(() => expect(pdfMock).toHaveBeenCalledWith(expect.objectContaining({ description: 'Add three posts', additionalCost: '850', reference: 'CO-20261005-H1' }), expect.any(Uint8Array), expect.any(Uint8Array)))
  expect(localStorage.getItem('scg:change-order:u1:p1:h1')).toContain('Add three posts')
})

it('presents the editable draft as a formal document', () => {
  render(<ChangeOrder initialDraft={original} projectName="Website" projectId="p1" historyId="abc123" userId="u1" />)
  const preview = screen.getByTestId('change-order-document-preview')
  expect(preview.querySelector('h2')?.textContent).toBe('CHANGE ORDER')
  expect(preview.textContent).toContain('DRAFT')
  expect(preview.textContent).toContain('CO-20261005-ABC123')
  expect(preview.textContent).toContain('1. Requested change')
  expect(preview.textContent).toContain('2. Commercial terms')
  expect(preview.textContent).not.toContain('Provider')
  expect(preview.textContent).not.toContain('Client email')
  expect(preview.textContent).toContain('Approved by')
  expect(preview.textContent).toContain('Date')
})

it('opens a legacy browser-saved draft with missing optional fields', () => {
  localStorage.setItem('scg:change-order:u1:p1:h1', JSON.stringify({
    createdAt: original.createdAt, language: 'en', projectName: 'Website', description: 'Legacy edit',
    estimatedHours: '4', additionalCost: '400', currency: 'USD',
  }))
  render(<ChangeOrder initialDraft={original} projectName="Website" projectId="p1" historyId="h1" userId="u1" />)
  expect((document.querySelector('#co-description') as HTMLTextAreaElement).value).toBe('Legacy edit')
  expect(screen.getByTestId('change-order-document-preview').textContent).toContain('Approved by')
})

it('restores browser-saved edits after remount', async () => {
  const view = render(<ChangeOrder initialDraft={original} projectName="Website" projectId="p1" historyId="h1" userId="u1" />)
  fireEvent.change(document.querySelector('#co-description')!, { target: { value: 'My own terms' } })
  await waitFor(() => expect(localStorage.getItem('scg:change-order:u1:p1:h1')).toContain('My own terms'))
  view.unmount()
  render(<ChangeOrder initialDraft={original} projectName="Website" projectId="p1" historyId="h1" userId="u1" />)
  expect((document.querySelector('#co-description') as HTMLTextAreaElement).value).toBe('My own terms')
})

it('changes currency without fetching rates or altering the amount', async () => {
  render(<ChangeOrder initialDraft={original} projectName="Website" projectId="p1" historyId="h1" userId="u1" />)
  fireEvent.change(document.querySelector('#co-currency')!, { target: { value: 'EUR' } })
  expect((document.querySelector('#co-additionalCost') as HTMLInputElement).value).toBe('1000')
  expect(vi.mocked(fetch)).not.toHaveBeenCalledWith('/api/exchange-rates', expect.anything())
})

it('keeps provider identity separate from client approval in saved draft and preview', async () => {
  render(<ChangeOrder initialDraft={original} projectName="Website" projectId="p1" historyId="h1" userId="u1" />)
  fireEvent.click(screen.getByText('additionalParameters'))
  fireEvent.change(document.querySelector('#co-providerName')!, { target: { value: 'North Studio' } })
  fireEvent.change(document.querySelector('#co-clientApproverName')!, { target: { value: 'Ana Ruiz' } })
  await waitFor(() => expect(localStorage.getItem('scg:change-order:u1:p1:h1')).toContain('North Studio'))
  const preview = screen.getByTestId('change-order-document-preview')
  expect(preview.textContent).toContain('North Studio')
  expect(preview.textContent).toContain('Ana Ruiz')
})

it('makes no-charge work explicit and restores the paid amount when switched back', async () => {
  render(<ChangeOrder initialDraft={original} projectName="Website" projectId="p1" historyId="h1" userId="u1" />)
  fireEvent.click(screen.getByRole('checkbox', { name: /^noAdditionalCharge/ }))
  expect(document.querySelector('#co-additionalCost')).toBeNull()
  expect(screen.getByTestId('change-order-document-preview').textContent).toContain('No additional charge')
  fireEvent.click(screen.getByRole('checkbox', { name: /^noAdditionalCharge/ }))
  expect((document.querySelector('#co-additionalCost') as HTMLInputElement).value).toBe('1000')
})

it('shows localized feedback instead of downloading unsupported glyphs', async () => {
  pdfMock.mockRejectedValue(new Error('unsupported_pdf_glyph'))
  render(<ChangeOrder initialDraft={original} projectName="Website" projectId="p1" historyId="h1" userId="u1" />)
  fireEvent.click(screen.getByRole('button', { name: 'downloadPdf' }))
  await screen.findByText('pdfLanguageUnsupported')
  expect(HTMLAnchorElement.prototype.click).not.toHaveBeenCalled()
})
