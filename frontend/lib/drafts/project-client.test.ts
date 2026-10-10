import { expect, it } from 'vitest'
import { snapshotProject } from './project-snapshot'
import { editableChangeOrder } from './document'
import { analysisFixture, projectSnapshotFixture } from './fixtures'
import { verifyDraftProof } from '@/tests/draft-proof-reference'
import { issueDraftProof } from '@/tests/draft-proof-fixture'
import { afterEach, vi } from 'vitest'
const project = { id: '10000000-0000-4000-8000-000000000001', ...projectSnapshotFixture, clientName: 'Server client', history: [] }
afterEach(() => vi.unstubAllEnvs())
it('seeds new Change Orders from current server client data, including a cleared client', () => {
  const details = { clientName: 'Obsolete local client', clientEmail: '', endDate: '2026-12-01' }
  expect(editableChangeOrder(analysisFixture, project, details, 'seed').clientName).toBe('Server client')
  expect(editableChangeOrder(analysisFixture, { ...project, clientName: null }, details, 'seed').clientName).toBe('')
})
it('signs canonical client metadata while keeping older snapshots valid', async () => {
  vi.stubEnv('AUTH_SECRET', 'client-test-secret-at-least-32-characters-long')
  const claims = { userId: project.id, projectId: project.id, request: 'Add a page', locale: 'en' as const, analysisSnapshot: analysisFixture, projectSnapshot: snapshotProject(project) }
  const proof = await issueDraftProof(claims)
  expect((await verifyDraftProof(proof, claims)).projectSnapshot.clientName).toBe('Server client')
  const legacy = { ...claims, projectSnapshot: projectSnapshotFixture }
  expect((await verifyDraftProof(await issueDraftProof(legacy), legacy)).projectSnapshot).toEqual(projectSnapshotFixture)
})
