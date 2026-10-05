import { NextResponse } from 'next/server'
import { parseCbrRates } from '@/lib/change-order/exchange-rates'

const CBR_DAILY_URL = 'https://www.cbr.ru/scripts/XML_daily.asp'

export async function GET() {
  try {
    const response = await fetch(CBR_DAILY_URL, {
      next: { revalidate: 900 },
      signal: AbortSignal.timeout(8_000),
    })
    if (!response.ok) throw new Error(`Exchange rate service returned ${response.status}`)
    const xml = new TextDecoder('windows-1251').decode(await response.arrayBuffer())
    return NextResponse.json(parseCbrRates(xml), { headers: { 'Cache-Control': 'private, max-age=900' } })
  } catch (error) {
    console.error(JSON.stringify({ event: 'exchange_rates_failed', message: error instanceof Error ? error.message : 'Unknown error' }))
    return NextResponse.json({ error: 'exchange_rates_unavailable' }, { status: 503, headers: { 'Cache-Control': 'no-store' } })
  }
}
