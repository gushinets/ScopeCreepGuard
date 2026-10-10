import { expect, it, vi, afterEach } from 'vitest'
import { verifyDraftProof } from '@/tests/draft-proof-reference'
import { issueDraftProof } from '@/tests/draft-proof-fixture'
import { analysisFixture, projectSnapshotFixture } from '@/lib/drafts/fixtures'
import { pythonProof } from './python-proof-fixture'
import { jwtVerify } from 'jose'
import { createHmac } from 'node:crypto'

afterEach(() => vi.unstubAllEnvs())

it('accepts Python proofs in JOSE and JOSE proofs in Python with both snapshots intact', async () => {
  vi.stubEnv('AUTH_SECRET', 'synthetic-cross-runtime-secret-at-least-32-characters')
  const claims = { userId: '10000000-0000-4000-8000-000000000001', projectId: '10000000-0000-4000-8000-000000000002', request: 'Añadir página 😀', locale: 'en' as const, analysisSnapshot: analysisFixture, projectSnapshot: projectSnapshotFixture }
  const proof = pythonProof('issue', claims)
  const decoded = await jwtVerify(proof, createHmac('sha256', process.env.AUTH_SECRET!).update('scg-draft-proof-v1').digest())
  expect(decoded.payload).toMatchObject({ userId: claims.userId, projectId: claims.projectId, request: claims.request, locale: 'en' })
  expect(await verifyDraftProof(proof, claims)).toEqual(claims)
  expect(JSON.parse(pythonProof('verify', claims, await issueDraftProof(claims)))).toEqual({ analysisSnapshot: analysisFixture, projectSnapshot: projectSnapshotFixture })
})
