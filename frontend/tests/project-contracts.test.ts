import { readFileSync, writeFileSync } from 'node:fs'
import { expect, it } from 'vitest'
import { parseProjectInput } from '@/lib/projects/validation'

const card = { name: ' Website ', scope: ' Five pages ', industry: 'Development', startDate: '2026-10-10', pricingModel: 'hourly', currency: 'EUR', hourlyRate: '000100.20' }
const cases = [
  {}, { ...card, clientName: ' Owner ', endDate: '2099-01-01', clientEmail: 'ignored@example.test' },
  { ...card, clientName: null }, { ...card, clientName: 42 },
  { ...card, name: '', scope: '', industry: 'Unknown' }, { ...card, scope: '\ufeff\u00a0' },
  { ...card, industry: 'development' }, { ...card, startDate: '2026-02-30' },
  { ...card, startDate: '0000-02-29' }, { ...card, pricingModel: 'other' },
  { ...card, currency: 'GBP' }, { ...card, hourlyRate: 12.3 },
  { ...card, hourlyRate: true }, { ...card, hourlyRate: '1.005' },
  { ...card, hourlyRate: '0' }, { ...card, hourlyRate: '1000000000000' },
  { ...card, hourlyRate: '\ufeff 999999999999.99 ' },
  { ...card, pricingModel: 'fixed', fixedPrice: '1234.50', hourlyRate: 'ignored' },
  { ...card, name: '\ufeff Name \u00a0', scope: '\u0085scope\u0085', clientName: '' },
]

it('freezes the existing project parser including error order and omission semantics', () => {
  const fixture = cases.map(body => ({ body, expected: parseProjectInput(body) }))
  const path = '../contracts/compatibility/any-640/projects.json'
  if (process.env.SCG_UPDATE_PROJECT_CONTRACTS === '1') writeFileSync(path, JSON.stringify(fixture, null, 2) + '\n')
  expect(fixture).toEqual(JSON.parse(readFileSync(path, 'utf8')))
})
