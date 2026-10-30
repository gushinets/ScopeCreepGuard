// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'
import { LocalizationProvider } from '@/shared/i18n/provider'
import { SessionProvider } from './session'
import { ConfirmEmail, VerifyEmail } from './email-confirmation'
import { publicDestination } from '@/shared/config/navigation'

afterEach(() => { cleanup(); vi.unstubAllGlobals(); window.history.replaceState(null, '', '/') })

function view() {
  document.cookie = 'locale=en; Path=/'
  return render(<LocalizationProvider><SessionProvider><MemoryRouter><ConfirmEmail /></MemoryRouter></SessionProvider></LocalizationProvider>)
}

it('never consumes a link on load; submits the fragment owner only on an explicit action', async () => {
  window.history.replaceState(null, '', '/confirm-email#userId=11111111-1111-4111-8111-111111111111&token=secret')
  const fetcher = vi.fn(async (path: RequestInfo | URL) => String(path) === '/api/auth/me'
    ? Response.json({ error: 'errors.authRequired' }, { status: 401 }) : Response.json({ ok: true }))
  vi.stubGlobal('fetch', fetcher)
  view()
  await screen.findByRole('button', { name: 'Confirm email' })
  expect(fetcher.mock.calls.some(([path]) => String(path).endsWith('/confirm'))).toBe(false)
  fireEvent.click(screen.getByRole('button', { name: 'Confirm email' }))
  await screen.findByText('Email confirmed')
  const call = fetcher.mock.calls.find(([path]) => String(path).endsWith('/confirm'))
  expect(call).toBeTruthy()
  const init = (fetcher.mock.calls as unknown as [string, RequestInit][]).find(([path]) => path.endsWith('/confirm'))![1]
  expect(JSON.parse(String(init.body))).toEqual({ userId: '11111111-1111-4111-8111-111111111111', token: 'secret' })
  expect(window.location.hash).toBe('')
})

it('does not turn a rejected token into success for an authenticated browser', async () => {
  window.history.replaceState(null, '', '/confirm-email#userId=11111111-1111-4111-8111-111111111111&token=bad')
  vi.stubGlobal('fetch', vi.fn(async (path: RequestInfo | URL) => String(path) === '/api/auth/me'
    ? Response.json({ user: { id: 'other', email: 'other@example.test', workspaceAccess: 'allowed' } })
    : Response.json({ error: 'errors.emailConfirmationInvalid' }, { status: 400 })))
  view()
  fireEvent.click(await screen.findByRole('button', { name: 'Confirm email' }))
  await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
  expect(screen.queryByText('Email confirmed')).toBeNull()
})

it('refreshes the original account and continues to a safe workspace destination', async () => {
  document.cookie = 'locale=en; Path=/'
  const owner = '11111111-1111-4111-8111-111111111111'
  window.history.replaceState(null, '', `/confirm-email#userId=${owner}&token=secret`)
  let confirmed = false
  vi.stubGlobal('fetch', vi.fn(async (path: RequestInfo | URL) => {
    if (String(path).endsWith('/confirm')) { confirmed = true; return Response.json({ ok: true }) }
    return Response.json({ user: { id: owner, email: 'owner@example.test', workspaceAccess: confirmed ? 'allowed' : 'email_confirmation_required' } })
  }))
  render(<LocalizationProvider><SessionProvider><MemoryRouter initialEntries={['/confirm-email?returnTo=%2Fhistory']}><Routes>
    <Route path="/confirm-email" element={<ConfirmEmail />} /><Route path="/history" element={<p>workspace reached</p>} />
  </Routes></MemoryRouter></SessionProvider></LocalizationProvider>)
  fireEvent.click(await screen.findByRole('button', { name: 'Confirm email' }))
  await screen.findByText('workspace reached')
})

it('does not reuse an identity request started before confirmation', async () => {
  document.cookie = 'locale=en; Path=/'
  const owner = '11111111-1111-4111-8111-111111111111'
  window.history.replaceState(null, '', `/confirm-email#userId=${owner}&token=secret`)
  let reads = 0
  vi.stubGlobal('fetch', vi.fn(async (path: RequestInfo | URL) => {
    if (String(path).endsWith('/confirm')) return Response.json({ ok: true })
    if (++reads === 1) return new Promise<Response>(() => {})
    return Response.json({ user: { id: owner, email: 'owner@example.test', workspaceAccess: 'allowed' } })
  }))
  render(<LocalizationProvider><SessionProvider><MemoryRouter initialEntries={['/confirm-email?returnTo=%2Fhistory']}><Routes>
    <Route path="/confirm-email" element={<ConfirmEmail />} /><Route path="/history" element={<p>workspace reached</p>} />
  </Routes></MemoryRouter></SessionProvider></LocalizationProvider>)
  fireEvent.click(await screen.findByRole('button', { name: 'Confirm email' }))
  await screen.findByText('workspace reached')
})

it('never resumes confirmation secrets or auth routes as product navigation', () => {
  for (const value of ['/confirm-email#token=secret', '/verify-email', '/unexpected', '/projects?token=secret', '/history#token=secret']) {
    expect(publicDestination(value)).toBe('/')
  }
  expect(publicDestination('/history?draft=working#reply')).toBe('/history?draft=working#reply')
})

it('reconstructs pending identity, shows neutral wording, and refreshes access on focus', async () => {
  document.cookie = 'locale=en; Path=/'
  let verified = false
  const fetcher = vi.fn(async () => Response.json({
    user: { id: 'owner', email: '<pending>@example.test', workspaceAccess: verified ? 'allowed' : 'email_confirmation_required' },
    emailConfirmation: { status: 'unknown', retryAfter: 60 },
  }))
  vi.stubGlobal('fetch', fetcher)
  render(<LocalizationProvider><SessionProvider><MemoryRouter initialEntries={['/verify-email?returnTo=%2Fhistory']}><Routes>
    <Route path="/verify-email" element={<VerifyEmail />} /><Route path="/history" element={<p>workspace reached</p>} />
  </Routes></MemoryRouter></SessionProvider></LocalizationProvider>)
  await screen.findByText('<pending>@example.test')
  expect(screen.getByRole('status').textContent).toContain('cannot confirm')
  expect((screen.getByRole('button', { name: 'Send confirmation email' }) as HTMLButtonElement).disabled).toBe(true)
  expect(document.querySelector('pending')).toBeNull()
  verified = true
  fireEvent(window, new Event('focus'))
  await screen.findByText('workspace reached')
  expect(fetcher).toHaveBeenCalledTimes(2)
})

it('uses server Retry-After on resend limits and sends explicit locale only', async () => {
  document.cookie = 'locale=en; Path=/'
  const fetcher = vi.fn(async (path: RequestInfo | URL) => String(path) === '/api/auth/me'
    ? Response.json({ user: { id: 'owner', email: 'owner@example.test', workspaceAccess: 'email_confirmation_required' }, emailConfirmation: { status: 'not_attempted', retryAfter: 0 } })
    : Response.json({ error: 'errors.emailResendLimited' }, { status: 429, headers: { 'Retry-After': '120' } }))
  vi.stubGlobal('fetch', fetcher)
  render(<LocalizationProvider><SessionProvider><MemoryRouter><VerifyEmail /></MemoryRouter></SessionProvider></LocalizationProvider>)
  fireEvent.click(await screen.findByRole('button', { name: 'Send confirmation email' }))
  await screen.findByRole('alert')
  expect(screen.getByText(/You can request another email in/).textContent).toContain('120')
  const call = (fetcher.mock.calls as unknown as [string, RequestInit][]).find(([path]) => path.endsWith('/resend'))!
  expect(JSON.parse(String(call[1].body))).toEqual({ locale: 'en' })
})

it('uses neutral last-send wording if the resend response is lost', async () => {
  document.cookie = 'locale=en; Path=/'
  vi.stubGlobal('fetch', vi.fn(async (path: RequestInfo | URL) => {
    if (String(path) === '/api/auth/me') return Response.json({ user: { id: 'owner', email: 'owner@example.test', workspaceAccess: 'email_confirmation_required' }, emailConfirmation: { status: 'accepted', retryAfter: 0 } })
    throw new TypeError('connection lost')
  }))
  render(<LocalizationProvider><SessionProvider><MemoryRouter><VerifyEmail /></MemoryRouter></SessionProvider></LocalizationProvider>)
  fireEvent.click(await screen.findByRole('button', { name: 'Send confirmation email' }))
  await screen.findByRole('alert')
  expect(screen.getByRole('status').textContent).toContain('cannot confirm')
})

it('replaces a local accepted resend with the newer server state after focus', async () => {
  document.cookie = 'locale=en; Path=/'
  let status = 'not_attempted'
  vi.stubGlobal('fetch', vi.fn(async (path: RequestInfo | URL) => {
    if (String(path) === '/api/auth/me') return Response.json({ user: { id: 'owner', email: 'owner@example.test', workspaceAccess: 'email_confirmation_required' }, emailConfirmation: { status, retryAfter: 0 } })
    return Response.json({ emailConfirmation: { status: 'accepted', retryAfter: 0 } })
  }))
  render(<LocalizationProvider><SessionProvider><MemoryRouter><VerifyEmail /></MemoryRouter></SessionProvider></LocalizationProvider>)
  fireEvent.click(await screen.findByRole('button', { name: 'Send confirmation email' }))
  await waitFor(() => expect(screen.getByRole('status').textContent).toContain('accepted'))
  status = 'unknown'
  fireEvent(window, new Event('focus'))
  await waitFor(() => expect(screen.getByRole('status').textContent).toContain('cannot confirm'))
})
