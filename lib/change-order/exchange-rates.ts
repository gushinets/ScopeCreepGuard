import type { Currency } from '@/lib/types'

export interface ExchangeRates {
  asOf: string
  rubPerUsd: number
  rubPerEur: number
}

function tag(block: string, name: string): string | null {
  return block.match(new RegExp(`<${name}>([^<]+)</${name}>`))?.[1] ?? null
}

function positiveDecimal(value: string | null): number {
  if (!value || !/^\d+(?:,\d+)?$/.test(value)) throw new Error('Invalid exchange rate')
  const number = Number(value.replace(',', '.'))
  if (!Number.isFinite(number) || number <= 0) throw new Error('Invalid exchange rate')
  return number
}

export function parseCbrRates(xml: string): ExchangeRates {
  const date = xml.match(/<ValCurs\b[^>]*\bDate="(\d{2})\.(\d{2})\.(\d{4})"/)
  if (!date) throw new Error('Exchange rate date missing')
  const asOf = `${date[3]}-${date[2]}-${date[1]}`
  if (new Date(`${asOf}T00:00:00Z`).toISOString().slice(0, 10) !== asOf) throw new Error('Invalid exchange rate date')

  const values: Partial<Record<'USD' | 'EUR', number>> = {}
  for (const block of xml.match(/<Valute\b[^>]*>[\s\S]*?<\/Valute>/g) ?? []) {
    const code = tag(block, 'CharCode')
    if (code !== 'USD' && code !== 'EUR') continue
    values[code] = positiveDecimal(tag(block, 'Value')) / positiveDecimal(tag(block, 'Nominal'))
  }
  if (!values.USD || !values.EUR) throw new Error('Exchange rates missing')
  return { asOf, rubPerUsd: values.USD, rubPerEur: values.EUR }
}

export function convertAmount(amount: string, from: Currency, to: Currency, rates: ExchangeRates): string | null {
  const trimmed = amount.trim().replace(',', '.')
  if (!/^\d+(?:\.\d{1,2})?$/.test(trimmed)) return null
  const number = Number(trimmed)
  if (!Number.isFinite(number) || number < 0 || number >= 1e12) return null
  const rubPerUnit: Record<Currency, number> = { RUB: 1, USD: rates.rubPerUsd, EUR: rates.rubPerEur }
  const converted = number * rubPerUnit[from] / rubPerUnit[to]
  if (!Number.isFinite(converted) || converted >= 1e12) return null
  return converted.toFixed(2)
}

export function isExchangeRates(value: unknown): value is ExchangeRates {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const rates = value as Record<string, unknown>
  return typeof rates.asOf === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(rates.asOf)
    && typeof rates.rubPerUsd === 'number' && Number.isFinite(rates.rubPerUsd) && rates.rubPerUsd > 0
    && typeof rates.rubPerEur === 'number' && Number.isFinite(rates.rubPerEur) && rates.rubPerEur > 0
}
