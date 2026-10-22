import { useChangeLocale } from './provider'
import { useLocale, useTranslations } from 'use-intl'
import { locales, type Locale } from '@/shared/i18n/config'
import { cn } from '@/shared/ui/utils'

export function LanguageSwitcher({ className }: { className?: string }) {
  const changeLocale = useChangeLocale()
  const currentLocale = useLocale()
  const t = useTranslations('language')

  async function switchLocale(nextLocale: Locale) {
    await changeLocale(nextLocale)
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
              ? 'bg-card text-foreground'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          {t(locale)}
        </button>
      ))}
    </div>
  )
}
