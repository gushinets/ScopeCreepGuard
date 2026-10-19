// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { useState } from 'react'
import { SessionProvider, useSession } from '@/features/auth'
import { apiJson } from '@/shared/api/client'
import { LocalizationProvider, useChangeLocale } from '@/shared/i18n/provider'
import { useLocale } from 'use-intl'

afterEach(() => { cleanup(); vi.unstubAllGlobals(); document.cookie = 'locale=; Max-Age=0; Path=/' })
function Identity() { const { user, error } = useSession(); return <p>{user?.id ?? error ?? 'anonymous'}</p> }
it('expires authenticated memory after a protected API returns 401', async () => {
  vi.stubGlobal('fetch', vi.fn(async input => String(input) === '/api/auth/me' ? Response.json({ user: { id: 'owner', email: 'x@example.test' } }) : Response.json({ error: 'errors.authRequired' }, { status: 401 })))
  render(<SessionProvider><Identity /></SessionProvider>)
  await screen.findByText('owner')
  await expect(apiJson('/api/v2/projects')).rejects.toMatchObject({ status: 401 })
  await waitFor(() => expect(screen.queryByText('owner')).toBeNull())
})
it('preserves an authenticated identity through a temporary service outage', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(Response.json({ user: { id: 'owner', email: 'x@example.test' } })).mockResolvedValue(Response.json({ error: 'errors.requestFailed' }, { status: 503 }))
  vi.stubGlobal('fetch', fetcher)
  render(<SessionProvider><Identity /></SessionProvider>)
  await screen.findByText('owner')
  fireEvent(window, new Event('focus'))
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2))
  expect(screen.getByText('owner')).toBeTruthy()
})
function Editor() {
  const [text, setText] = useState('client edit')
  const change = useChangeLocale(), locale = useLocale()
  return <><input aria-label="editor" value={text} onChange={event => setText(event.target.value)} /><p>{locale}</p><button onClick={() => { void change('en') }}>English</button></>
}
it('changes interface locale without remounting or clearing editor state', async () => {
  document.cookie = 'locale=ru; Path=/'
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({ ok: true })))
  render(<LocalizationProvider><Editor /></LocalizationProvider>)
  fireEvent.change(screen.getByLabelText('editor'), { target: { value: 'my newer text' } })
  fireEvent.click(screen.getByText('English'))
  await screen.findByText('en')
  expect((screen.getByLabelText('editor') as HTMLInputElement).value).toBe('my newer text')
  expect(document.documentElement.lang).toBe('en')
})
