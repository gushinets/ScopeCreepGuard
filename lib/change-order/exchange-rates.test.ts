import { describe, expect, it } from 'vitest'
import { convertAmount, parseCbrRates } from './exchange-rates'

const xml = `<?xml version="1.0" encoding="windows-1251"?>
<ValCurs Date="03.10.2026" name="Foreign Currency Market">
  <Valute><CharCode>USD</CharCode><Nominal>1</Nominal><Value>83,4839</Value></Valute>
  <Valute><CharCode>EUR</CharCode><Nominal>10</Nominal><Value>943,2010</Value></Valute>
</ValCurs>`

describe('Bank of Russia exchange rates', () => {
  it('parses dated RUB rates and honors the currency nominal', () => {
    expect(parseCbrRates(xml)).toEqual({ asOf: '2026-10-03', rubPerUsd: 83.4839, rubPerEur: 94.3201 })
  })

  it('rejects missing or invalid rates instead of inventing a comparison', () => {
    expect(() => parseCbrRates(xml.replace('<CharCode>EUR</CharCode>', '<CharCode>GBP</CharCode>'))).toThrow()
    expect(() => parseCbrRates(xml.replace('<Value>83,4839</Value>', '<Value>0</Value>'))).toThrow()
  })

  it('converts the selected amount to both other currencies', () => {
    const rates = parseCbrRates(xml)
    expect(convertAmount('100.00', 'USD', 'RUB', rates)).toBe('8348.39')
    expect(convertAmount('100.00', 'USD', 'EUR', rates)).toBe('88.51')
    expect(convertAmount('100,00', 'USD', 'EUR', rates)).toBe('88.51')
    expect(convertAmount('8348.39', 'RUB', 'USD', rates)).toBe('100.00')
  })

  it('does not convert blank or nonnumeric user terms', () => {
    const rates = parseCbrRates(xml)
    expect(convertAmount('', 'USD', 'EUR', rates)).toBeNull()
    expect(convertAmount('about 100', 'USD', 'EUR', rates)).toBeNull()
  })
})
