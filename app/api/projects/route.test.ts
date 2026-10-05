import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  getCurrentUser: vi.fn(), values: vi.fn(), returning: vi.fn(),
}))
vi.mock('@/lib/auth/current-user', () => ({ getCurrentUser: mocks.getCurrentUser }))
vi.mock('@/lib/db', () => ({ db: { insert: () => ({ values: mocks.values }) } }))
vi.mock('@/lib/projects/data', () => ({ loadProjectsForUser: vi.fn() }))

import { POST } from './route'

const input = { name: 'Website', scope: 'Build 5 pages', industry: 'Design', startDate: '2026-10-01', pricingModel: 'hourly', currency: 'EUR', hourlyRate: '120', fixedPrice: '', clientName: 'Local only', clientEmail: 'client@example.test', endDate: '2026-12-01' }

beforeEach(() => {
  mocks.getCurrentUser.mockResolvedValue({ id: 'user-1' })
  mocks.returning.mockResolvedValue([{ id: 'project-1', userId: 'user-1', name: 'Website', scope: 'Build 5 pages', industry: 'Design', startDate: '2026-10-01', pricingModel: 'hourly', currency: 'EUR', hourlyRate: '120.00', fixedPrice: null, client: null, lastChecked: null }])
  mocks.values.mockReturnValue({ returning: mocks.returning })
})

describe('project persistence', () => {
  it('writes required commercial terms while excluding optional browser details', async () => {
    const response = await POST(new Request('http://localhost/api/projects', { method: 'POST', body: JSON.stringify(input) }) as never)
    expect(response.status).toBe(201)
    expect(mocks.values).toHaveBeenCalledWith(expect.objectContaining({ startDate: '2026-10-01', pricingModel: 'hourly', currency: 'EUR', hourlyRate: '120.00', fixedPrice: null }))
    const written = mocks.values.mock.lastCall?.[0]
    expect(written).not.toHaveProperty('client')
    expect(written).not.toHaveProperty('clientName')
    expect(written).not.toHaveProperty('endDate')
    const data = await response.json()
    expect(data.project.hourlyRate).toBe('120.00')
  })

  it('rejects missing commercial fields before database insertion', async () => {
    mocks.values.mockClear()
    const response = await POST(new Request('http://localhost/api/projects', { method: 'POST', body: JSON.stringify({ ...input, hourlyRate: '' }) }) as never)
    expect(response.status).toBe(400)
    expect(mocks.values).not.toHaveBeenCalled()
  })
})
