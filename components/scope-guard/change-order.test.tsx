// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import type { EditableDraft } from '@/lib/change-order/document'
import { ChangeOrder } from './change-order'

const pdfMock = vi.hoisted(() => vi.fn())
vi.mock('@/lib/change-order/pdf', () => ({ createChangeOrderPdf: pdfMock }))
vi.mock('next-intl', () => ({ useLocale: () => 'en', useTranslations: () => (key: string) => key }))

const original: EditableDraft = {
  createdAt: '2026-10-05T12:00:00Z', language: 'en', projectName: 'Website', description: 'Add blog',
  estimatedHours: '10', additionalCost: '1000', currency: 'USD', timelineImpact: 'Two days',
  rationale: 'Extra work', note: '', clientName: '', clientEmail: '', endDate: '',
  additionalTerms: '', approvedBy: '', approvalDate: '',
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

it('copies and exports the current edited draft', async () => {
  render(<ChangeOrder initialDraft={original} projectName="Website" projectId="p1" historyId="h1" userId="u1" />)
  fireEvent.change(document.querySelector('#co-description')!, { target: { value: 'Add three posts' } })
  fireEvent.change(document.querySelector('#co-additionalCost')!, { target: { value: '850' } })
  fireEvent.click(screen.getByRole('button', { name: 'copy' }))
  await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith(expect.stringContaining('850 USD')))
  expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Add three posts')
  fireEvent.click(screen.getByRole('button', { name: 'downloadPdf' }))
  await waitFor(() => expect(pdfMock).toHaveBeenCalledWith(expect.objectContaining({ description: 'Add three posts', additionalCost: '850' }), expect.any(Uint8Array)))
  expect(localStorage.getItem('scg:change-order:u1:p1:h1')).toContain('Add three posts')
})

it('restores browser-saved edits after remount', async () => {
  const view = render(<ChangeOrder initialDraft={original} projectName="Website" projectId="p1" historyId="h1" userId="u1" />)
  fireEvent.change(document.querySelector('#co-description')!, { target: { value: 'My own terms' } })
  await waitFor(() => expect(localStorage.getItem('scg:change-order:u1:p1:h1')).toContain('My own terms'))
  view.unmount()
  render(<ChangeOrder initialDraft={original} projectName="Website" projectId="p1" historyId="h1" userId="u1" />)
  expect((document.querySelector('#co-description') as HTMLTextAreaElement).value).toBe('My own terms')
})
