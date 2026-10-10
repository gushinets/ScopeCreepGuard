import { describe, expect, it } from 'vitest'
import { parseCreateDraft, parseDraftDocument } from '@/tests/draft-validation-reference'
import { analysisFixture, documentFixture, projectSnapshotFixture } from './fixtures'

const claims = { userId: 'owner', projectId: '10000000-0000-4000-8000-000000000001', request: 'Add another page', locale: 'en' as const, analysisSnapshot: analysisFixture, projectSnapshot: projectSnapshotFixture }
describe('draft validation', () => {
  it('preserves the complete original snapshot and editable state independently', () => {
    const input = parseCreateDraft({
      projectId: '10000000-0000-4000-8000-000000000001',
      request: 'Add another page', locale: 'en',
      idempotencyKey: '10000000-0000-4000-8000-000000000002',
      analysisSnapshot: { ...analysisFixture, replies: { warm: 'Forged', neutral: 'Forged', firm: 'Forged' } }, draftDocument: documentFixture,
    }, claims)
    expect(input.analysisSnapshot.changeOrder.additionalCost).toBe('200')
    expect(input.analysisSnapshot.draftCreatedAt).toBe('2026-10-06T12:00:00.000Z')
    expect(input.draftDocument.changeOrder?.additionalCost).toBe('175')
    expect(input.draftDocument.reply.text).toBe('My edited reply')
    expect(input.draftDocument.changeOrder?.providerName).toBe('North Studio')
  })

  it('accepts empty editable fields without losing them', () => {
    const input = { ...documentFixture, reply: { ...documentFixture.reply, text: '' }, changeOrder: { ...documentFixture.changeOrder!, description: '', estimatedHours: '' } }
    expect(parseDraftDocument(input, 'en', analysisFixture).changeOrder?.description).toBe('')
  })

  it.each([
    { ...documentFixture, version: 2 },
    { ...documentFixture, reply: { ...documentFixture.reply, tone: 'aggressive' } },
    { ...documentFixture, changeOrder: { ...documentFixture.changeOrder!, noAdditionalCharge: 'yes' } },
    { ...documentFixture, result: { ...analysisFixture, verdict: 'in_scope' } },
    { ...documentFixture, result: { ...analysisFixture, citations: ['Invented scope'] } },
    { ...documentFixture, changeOrder: { ...documentFixture.changeOrder!, language: 'de' } },
  ])('rejects malformed or altered analysis/document data', (input) => {
    expect(() => parseDraftDocument(input, 'en', analysisFixture)).toThrow()
  })

  it('rejects invalid IDs, blank requests, unsupported locale and oversized bodies', () => {
    const body = { projectId: '10000000-0000-4000-8000-000000000001', idempotencyKey: '10000000-0000-4000-8000-000000000002', request: 'Add page', locale: 'en', analysisSnapshot: analysisFixture, draftDocument: documentFixture }
    for (const override of [{ projectId: 'bad' }, { idempotencyKey: 'bad' }, { request: '' }, { locale: 'de' }, { request: 'x'.repeat(100001) }]) {
      expect(() => parseCreateDraft({ ...body, ...override }, claims)).toThrow()
    }
  })
})
