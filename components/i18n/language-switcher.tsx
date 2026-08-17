'use client'

import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { locales, type Locale } from '@/i18n/config'
import { cn } from '@/lib/utils'

export function LanguageSwitcher({ className }: { className?: string }) {
  const router = useRouter()
  const currentLocale = useLocale()
  const t = useTranslations('language')

  async function switchLocale(nextLocale: Locale) {
    try {
      const response = await fetch('/api/locale', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ locale: nextLocale }),
      })

      if (!response.ok) {
        throw new Error(`Locale switch failed with status ${response.status}`)
      }
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'locale_switch_failed',
          locale: nextLocale,
          message: error instanceof Error ? error.message : 'Unknown locale error',
        }),
      )
      throw error
    }

    router.refresh()
  }

  return (
    <div
      role="radiogroup"
      aria-label={t('ariaLabel')}
      className={cn(
        'inline-flex rounded-lg border border-border bg-muted p-0.5',
        className,
      )}
    >
      {locales.map((locale) => (
        <button
          key={locale}
          type="button"
          role="radio"
          aria-checked={currentLocale === locale}
          onClick={() => {
            void switchLocale(locale)
          }}
          className={cn(
            'rounded-md px-2.5 py-1 text-xs font-medium uppercase transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            currentLocale === locale
              ? 'bg-card text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          {t(locale)}
        </button>
      ))}
    </div>
  )
}
