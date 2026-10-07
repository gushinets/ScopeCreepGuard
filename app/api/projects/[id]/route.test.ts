import { beforeEach, expect, it, vi } from 'vitest'
import { and, eq } from 'drizzle-orm'
import { projects } from '@/lib/db/schema'
const mocks = vi.hoisted(() => ({ user: vi.fn(), load: vi.fn(), update: vi.fn(), remove: vi.fn(), set: vi.fn(), where: vi.fn(), returning: vi.fn() }))
vi.mock('@/lib/auth/current-user', () => ({ getCurrentUser: mocks.user }))
vi.mock('@/lib/db', () => ({ db: { update: mocks.update, delete: mocks.remove } }))
vi.mock('@/lib/projects/data', async original => ({ ...await original<typeof import('@/lib/projects/data')>(), loadProjectForUser: mocks.load }))
import { PATCH, DELETE } from './route'
const input = { name: 'Renamed', clientName: ' Acme ', scope: 'New agreed scope', industry: 'Marketing', startDate: '2026-10-03', pricingModel: 'hourly', currency: 'EUR', hourlyRate: '125', fixedPrice: '' }
const row = { id: 'p1', userId: 'u1', name: input.name, client: 'Acme', scope: input.scope, industry: input.industry, startDate: input.startDate, pricingModel: input.pricingModel, currency: input.currency, hourlyRate: '125.00', fixedPrice: null, lastChecked: null }
const context = { params: Promise.resolve({ id: 'p1' }) }
const request = (body = input) => new Request('http://localhost/api/projects/p1', { method: 'PATCH', body: JSON.stringify(body) })
beforeEach(() => {
  vi.clearAllMocks()
  mocks.user.mockResolvedValue({ id: 'u1' })
  mocks.load.mockResolvedValue({ ...row, history: [{ id: 'h1' }] })
  mocks.update.mockReturnValue({ set: mocks.set })
  mocks.set.mockReturnValue({ where: mocks.where })
  mocks.remove.mockReturnValue({ where: mocks.where })
  mocks.where.mockReturnValue({ returning: mocks.returning })
  mocks.returning.mockResolvedValue([row])
})
it('persists every supported field and returns the persisted project with history', async () => {
  const response = await PATCH(request(), context)
  expect(response.status).toBe(200)
  expect(mocks.load).toHaveBeenCalledWith('p1', 'u1')
  expect(mocks.set).toHaveBeenCalledWith({ name: input.name, client: 'Acme', scope: input.scope, industry: input.industry, startDate: input.startDate, pricingModel: input.pricingModel, currency: input.currency, hourlyRate: '125.00', fixedPrice: null })
  expect(mocks.where).toHaveBeenCalledWith(and(eq(projects.id, 'p1'), eq(projects.userId, 'u1')))
  expect(await response.json()).toMatchObject({ project: { ...input, clientName: 'Acme', hourlyRate: '125.00', fixedPrice: null, history: [{ id: 'h1' }] } })
})
it('switches to fixed pricing and clears the hourly amount', async () => {
  await PATCH(request({ ...input, pricingModel: 'fixed', fixedPrice: '5000' }), context)
  expect(mocks.set).toHaveBeenCalledWith(expect.objectContaining({ hourlyRate: null, fixedPrice: '5000.00' }))
})
it('preserves client name for older callers that omit it', async () => {
  const { clientName: omitted, ...legacy } = input
  void omitted
  await PATCH(request(legacy as typeof input), context)
  expect(mocks.set.mock.lastCall?.[0]).not.toHaveProperty('client')
})
it.each([PATCH, DELETE])('rejects unauthenticated mutations', async handler => {
  mocks.user.mockResolvedValue(null)
  expect((await handler(request(), context)).status).toBe(401)
  expect(mocks.update).not.toHaveBeenCalled()
  expect(mocks.remove).not.toHaveBeenCalled()
})
it('returns 404 when editing another user project', async () => {
  mocks.load.mockResolvedValue(null)
  expect((await PATCH(request(), context)).status).toBe(404)
  expect(mocks.update).not.toHaveBeenCalled()
})
it('rejects invalid commercial terms before updating', async () => {
  expect((await PATCH(request({ ...input, hourlyRate: '0' }), context)).status).toBe(400)
  expect(mocks.update).not.toHaveBeenCalled()
})
it('deletes only the authenticated owner project', async () => {
  expect(await (await DELETE(request(), context)).json()).toEqual({ ok: true })
  expect(mocks.remove).toHaveBeenCalledWith(projects)
  expect(mocks.where).toHaveBeenCalledWith(and(eq(projects.id, 'p1'), eq(projects.userId, 'u1')))
})
it('returns 404 when deletion does not match an owned project', async () => {
  mocks.returning.mockResolvedValue([])
  expect((await DELETE(request(), context)).status).toBe(404)
})
