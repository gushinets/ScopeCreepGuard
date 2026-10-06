import type { Locale } from '@/i18n/config'

/** Accept only bounded, structurally valid language tags, never prompt text. */
export function normalizeLanguageTag(value: unknown): string | undefined {
  if (typeof value !== 'string' || value.length > 100 || !/^[a-zA-Z]{2,8}(?:-[a-zA-Z0-9]{1,8})*$/.test(value.trim())) return undefined
  try {
    const tag = Intl.getCanonicalLocales(value.trim())[0]
    return ['other', 'und', 'zxx', 'mul'].includes(tag.split('-')[0]) ? undefined : tag
  }
  catch { return undefined }
}

export function resolveClientLanguage(detected: unknown, locale: Locale, override?: unknown): string {
  return normalizeLanguageTag(override) ?? normalizeLanguageTag(detected) ?? locale
}

/** Languages whose normal script is covered by the bundled Noto Sans fonts.
 * Regional variants are supported; extensions and unexpected script overrides
 * are excluded because they can change date digits or require complex shaping.
 */
export const PDF_CLIENT_LANGUAGES = ['ru', 'en', 'es', 'de', 'fr', 'it', 'nl', 'pl', 'pt', 'tr', 'uk', 'bg', 'el', 'cs', 'sk', 'hr', 'ro', 'hu', 'fi', 'sv', 'da', 'nb', 'et', 'lv', 'lt', 'id'] as const

export function supportedClientLanguage(value: unknown): string | undefined {
  const tag = normalizeLanguageTag(value)
  if (!tag || !/^[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-[A-Z]{2}|-\d{3})?$/.test(tag)) return undefined
  const locale = new Intl.Locale(tag)
  if (!(PDF_CLIENT_LANGUAGES as readonly string[]).includes(locale.language)) return undefined
  const script = ['ru', 'uk', 'bg'].includes(locale.language) ? 'Cyrl' : locale.language === 'el' ? 'Grek' : 'Latn'
  return !locale.script || locale.script === script ? tag : undefined
}
