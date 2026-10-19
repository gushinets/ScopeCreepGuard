import { IntlProvider } from 'use-intl'
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import en from './messages/en.json'
import ru from './messages/ru.json'
import { defaultLocale, isLocale, localeCookieName, type Locale } from './config'
import { apiJson } from '../api/client'

const catalogs = { en, ru }
const LocaleContext = createContext<((locale: Locale) => Promise<void>) | null>(null)

function initialLocale(): Locale {
  const value = document.cookie.split(';').map(part => part.trim()).find(part => part.startsWith(`${localeCookieName}=`))?.split('=')[1]
  return value && isLocale(value) ? value : defaultLocale
}

export function LocalizationProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState(initialLocale)
  useEffect(() => {
    document.documentElement.lang = locale
    document.title = catalogs[locale].meta.title
    document.querySelector('meta[name="description"]')?.setAttribute('content', catalogs[locale].meta.description)
  }, [locale])
  async function changeLocale(next: Locale) {
    await apiJson('/api/locale', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ locale: next }) })
    setLocale(next)
  }
  return <LocaleContext.Provider value={changeLocale}><IntlProvider locale={locale} messages={catalogs[locale]}>{children}</IntlProvider></LocaleContext.Provider>
}

export function useChangeLocale() {
  const change = useContext(LocaleContext)
  if (!change) throw new Error('Localization provider is missing')
  return change
}
