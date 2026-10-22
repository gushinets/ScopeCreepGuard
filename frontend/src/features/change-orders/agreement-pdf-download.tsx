import { useEffect, useRef, useState } from 'react'
import { Download } from 'lucide-react'
import { useTranslations } from 'use-intl'
import { ApiClientError } from '@/shared/api/client'
import { ERROR_CODES, type ErrorCode } from '@/shared/api/errors'
import { supportedClientLanguage } from '@/shared/i18n/client-language'
import { Button } from '@/shared/ui/button'

export type PdfDownload = (signal: AbortSignal) => Promise<{ blob: Blob; filename: string }>

/** Direct downloads share cancellation and error handling in the editor and History. */
export function AgreementPdfDownload({ language, download, disabled = false }: { language: string; download: PdfDownload; disabled?: boolean }) {
  const t = useTranslations('changeOrder')
  const messages = useTranslations()
  const controller = useRef<AbortController | null>(null)
  const [busy, setBusy] = useState(false)
  const [downloaded, setDownloaded] = useState(false)
  const [error, setError] = useState<ErrorCode | ''>('')
  useEffect(() => () => controller.current?.abort(), [])
  async function run() {
    if (controller.current) return
    const request = new AbortController()
    controller.current = request
    setBusy(true); setDownloaded(false); setError('')
    try {
      const file = await download(request.signal)
      if (request.signal.aborted) return
      const url = URL.createObjectURL(file.blob)
      const anchor = document.createElement('a')
      anchor.href = url; anchor.download = file.filename; anchor.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 10_000)
      setDownloaded(true)
    } catch (failure) {
      if (!request.signal.aborted) setError(failure instanceof ApiClientError ? failure.code : ERROR_CODES.pdfExportFailed)
    } finally {
      if (controller.current === request) { controller.current = null; setBusy(false) }
    }
  }
  return <>
    <Button type="button" variant="outline" disabled={disabled || busy || !supportedClientLanguage(language)} onClick={() => void run()}><Download aria-hidden="true" />{t(busy ? 'downloading' : 'downloadPdf')}</Button>
    {busy && <Button type="button" variant="ghost" onClick={() => controller.current?.abort()}>{t('cancelDownload')}</Button>}
    {!supportedClientLanguage(language) && <p role="alert" className="w-full text-sm">{t('pdfLanguageUnsupported')}</p>}
    {error && <p role="alert" className="w-full text-sm text-outscope-text">{messages(error)}</p>}
    {downloaded && <p role="status" className="w-full text-xs text-muted-foreground">{t('downloaded')}</p>}
  </>
}
