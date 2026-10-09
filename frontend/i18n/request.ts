import { cookies } from 'next/headers'
import { getRequestConfig } from 'next-intl/server'
import en from '../messages/en.json'
import ru from '../messages/ru.json'
import {
  defaultLocale,
  isLocale,
  localeCookieName,
  type Locale,
} from './config'

const catalogs = {
  en,
  ru,
} as const

async function resolveLocale(): Promise<Locale> {
  const cookieStore = await cookies()
  const cookieLocale = cookieStore.get(localeCookieName)?.value

  if (!cookieLocale) return defaultLocale
  if (isLocale(cookieLocale)) return cookieLocale

  console.error(
    JSON.stringify({
      event: 'locale_cookie_invalid',
      cookie: localeCookieName,
      value: cookieLocale,
    }),
  )
  throw new Error(`Invalid locale cookie: ${cookieLocale}`)
}

export default getRequestConfig(async () => {
  const locale = await resolveLocale()

  return {
    locale,
    messages: catalogs[locale],
  }
})
