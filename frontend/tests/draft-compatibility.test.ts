import { readFileSync, writeFileSync } from 'node:fs'
import { expect, it } from 'vitest'
import { parseDraftDocument, parseCreateDraftEnvelope } from './draft-validation-reference'

const file = '../contracts/compatibility/any-640/drafts.json'
const base = JSON.parse(readFileSync('../backend/tests/fixtures/contracts.json', 'utf8'))
const mutations = [
  { name: 'original', path: '', value: null },
  { name: 'empty editable description', path: 'changeOrder.description', value: '' },
  { name: 'legacy date', path: 'changeOrder.createdAt', value: 'October 6, 2026' },
  { name: 'two-digit slash date', path: 'changeOrder.createdAt', value: '10/10/26' },
  { name: 'legacy space timestamp', path: 'changeOrder.createdAt', value: '2026-10-10 09:00' },
  { name: 'lowercase ISO timestamp', path: 'changeOrder.createdAt', value: '2026-10-10t09:00:00.000z' },
  { name: 'array currency compatibility', path: 'changeOrder.currency', value: [] },
  { name: 'array tone compatibility', path: 'reply.tone', value: ['firm'] },
  { name: 'missing reference', path: 'changeOrder.reference', remove: true },
  { name: 'null reference', path: 'changeOrder.reference', value: null },
  { name: 'missing materials', path: 'clientMaterials', remove: true },
  { name: 'missing change order', path: 'changeOrder', remove: true },
  { name: 'null change order', path: 'changeOrder', value: null },
  { name: 'boolean version', path: 'version', value: true },
  { name: 'immutable summary', path: 'result.summary', value: 'changed' },
  { name: 'immutable null request language', path: 'result.requestLanguage', value: null },
  { name: 'ai unknown field', path: 'changeOrder.aiValues.unknown', value: 'x' },
  { name: 'null ai values', path: 'changeOrder.aiValues', value: null },
  { name: 'null editor labels', path: 'changeOrder.changeOrderLabels', value: null },
  { name: 'unknown properties discarded', path: 'ignored', value: 'small' },
  { name: 'UTF16 exact limit', path: 'reply.text', value: '😀', repeat: 50000 },
  { name: 'UTF16 over limit', path: 'reply.text', value: '😀', repeat: 50001 },
  { name: 'UTF8 ignored size overflow', path: 'ignored', value: 'Ж', repeat: 500000 },
]

it('matches frozen TypeScript draft validation and normalization vectors', () => {
  const observations = mutations.map(mutation => {
    const document = structuredClone(base.document)
    if (mutation.path) {
      const keys = mutation.path.split('.')
      let node = document
      for (const key of keys.slice(0, -1)) node = node[key]
      const key = keys.at(-1)!
      if ('remove' in mutation) delete node[key]
      else node[key] = 'repeat' in mutation ? String(mutation.value).repeat(mutation.repeat!) : mutation.value
    }
    try { return { ...mutation, valid: true, ...(!('repeat' in mutation) ? { output: parseDraftDocument(document, 'en', base.analysis) } : (parseDraftDocument(document, 'en', base.analysis), {})) } }
    catch { return { ...mutation, valid: false } }
  })
  const snapshot = { source: 'Frozen pre-cutover TypeScript parser; no production imports', base, documents: observations }
  if (process.env.SCG_UPDATE_DRAFT_VECTORS === '1') writeFileSync(file, JSON.stringify(snapshot, null, 2) + '\n')
  expect(snapshot).toEqual(JSON.parse(readFileSync(file, 'utf8')))
})

it('uses the complete envelope JSON size and exact UUID syntax before proof parsing', () => {
  const envelope = { projectId: 'ABCDEFAB-1234-5678-90AB-ABCDEFABCDEF', idempotencyKey: '10000000-0000-4000-8000-000000000001', request: ' \ufeffRequest\ufeff ', locale: 'en', proof: null, draftDocument: {} }
  expect(parseCreateDraftEnvelope(envelope)).toMatchObject({ projectId: envelope.projectId, request: 'Request' })
  expect(() => parseCreateDraftEnvelope({ ...envelope, projectId: '{' + envelope.projectId + '}' })).toThrow()
  expect(() => parseCreateDraftEnvelope({ ...envelope, ignored: 'Ж'.repeat(500000) })).toThrow()
})
