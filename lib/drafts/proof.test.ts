
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { createSessionToken } from '@/lib/auth/session'
import { analysisFixture } from './fixtures'
import { issueDraftProof, verifyDraftProof } from './proof'

const claims = {
  userId: '10000000-0000-4000-8000-000000000001',
  projectId: '10000000-0000-4000-8000-000000000002',
  request: 'Add another page', locale: 'en' as const,
  analysisSnapshot: analysisFixture,
  projectSnapshot: {
    version: 1 as const, name: 'Website', industry: 'Development' as const,
    scope: 'Five pages only.', startDate: '2026-01-01', endDate: '2026-12-01',
    pricingModel: 'hourly' as const, currency: 'EUR' as const, hourlyRate: '100', fixedPrice: null,
    documentLanguage: 'en',
  },
}
beforeEach(() => { vi.stubEnv('AUTH_SECRET', 'test-secret-with-at-least-32-characters'); vi.useFakeTimers(); vi.setSystemTime(new Date('2026-10-07T09:00:00Z')) })
afterEach(() => { vi.unstubAllEnvs(); vi.useRealTimers() })
it('authenticates complete analysis and project claims', async () => {
  const proof = await issueDraftProof(claims)
  const verified = await verifyDraftProof(proof, claims)
  expect(verified.analysisSnapshot).toEqual(analysisFixture)
  expect(verified.projectSnapshot).toEqual(claims.projectSnapshot)
})
it('rejects a changed signed payload and session tokens', async () => {
  const proof = await issueDraftProof(claims)
  const [header, raw, signature] = proof.split('.')
  const payload = JSON.parse(Buffer.from(raw, 'base64url').toString())
  payload.analysisSnapshot.verdict = 'in_scope'
  const forged = [header, Buffer.from(JSON.stringify(payload)).toString('base64url'), signature].join('.')
  await expect(verifyDraftProof(forged, claims)).rejects.toThrow()
  const session = await createSessionToken({ id: claims.userId, email: 'owner@example.test' })
  await expect(verifyDraftProof(session, claims)).rejects.toThrow()
})
it.each([
  { userId: 'another-user' }, { projectId: 'another-project' },
  { request: 'Different request' }, { locale: 'ru' as const },
])('rejects proofs used with mismatched user/project/request/locale', async (override) => {
  const proof = await issueDraftProof(claims)
  await expect(verifyDraftProof(proof, { ...claims, ...override })).rejects.toThrow()
})
it('rejects expired and malformed proofs', async () => {
  const proof = await issueDraftProof(claims)
  vi.setSystemTime(new Date('2026-10-07T10:00:01Z'))
  await expect(verifyDraftProof(proof, claims)).rejects.toThrow()
  await expect(verifyDraftProof('not-a-token', claims)).rejects.toThrow()
})
