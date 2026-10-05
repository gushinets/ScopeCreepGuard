import { afterEach, expect, it, vi } from 'vitest'
import { GET } from './route'

afterEach(() => vi.unstubAllGlobals())

it('returns current dated USD and EUR rates from the Bank of Russia', async () => {
  const xml = '<ValCurs Date="03.10.2026"><Valute><CharCode>USD</CharCode><Nominal>1</Nominal><Value>83,4839</Value></Valute><Valute><CharCode>EUR</CharCode><Nominal>1</Nominal><Value>94,3201</Value></Valute></ValCurs>'
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(new TextEncoder().encode(xml), { status: 200 })))
  const response = await GET()
  expect(response.status).toBe(200)
  expect(await response.json()).toEqual({ asOf: '2026-10-03', rubPerUsd: 83.4839, rubPerEur: 94.3201 })
})

it('does not return made-up rates when the provider is unavailable', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
  const response = await GET()
  expect(response.status).toBe(503)
  expect(await response.json()).not.toHaveProperty('rubPerUsd')
})
