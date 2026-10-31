// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router'
import { LocalizationProvider } from '@/shared/i18n/provider'
import { SessionProvider } from './session'
import { PasswordRecovery } from './password-recovery'

afterEach(() => { cleanup(); vi.unstubAllGlobals(); window.history.replaceState(null, '', '/') })

it('does not consume a link before explicit matching-password submission', async () => {
  document.cookie = 'locale=en; Path=/'
  window.history.replaceState(null, '', '/reset-password#userId=11111111-1111-4111-8111-111111111111&token=abcdefghijklmnopqrstuv')
  const fetcher = vi.fn(async (path: RequestInfo | URL) => String(path) === '/api/auth/me'
    ? Response.json({ error: 'errors.authRequired' }, { status: 401 }) : Response.json({ ok: true }))
  vi.stubGlobal('fetch', fetcher)
  render(<LocalizationProvider><SessionProvider><MemoryRouter><PasswordRecovery reset /></MemoryRouter></SessionProvider></LocalizationProvider>)
  expect(fetcher.mock.calls.some(([path]) => String(path).endsWith('/reset'))).toBe(false)
  fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'replacement-password' } })
  fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'different-password' } })
  fireEvent.click(screen.getByRole('button', { name: 'Change password' }))
  await screen.findByRole('alert')
  expect(fetcher.mock.calls.some(([path]) => String(path).endsWith('/reset'))).toBe(false)
  fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'replacement-password' } })
  fireEvent.click(screen.getByRole('button', { name: 'Change password' }))
  await screen.findByRole('heading', { name: 'Password changed' })
  expect(window.location.hash).toBe('')
  expect(fetcher.mock.calls.filter(([path]) => String(path).endsWith('/login'))).toHaveLength(0)
})

it('keeps an authenticated different account until the explicit sign-out action', async () => {
  document.cookie = 'locale=en; Path=/'
  const owner = '11111111-1111-4111-8111-111111111111'
  window.history.replaceState(null, '', `/reset-password#userId=${owner}&token=abcdefghijklmnopqrstuv`)
  const calls: [string, RequestInit | undefined][] = []
  vi.stubGlobal('fetch', vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
    calls.push([String(path), init])
    return String(path) === '/api/auth/me'
      ? Response.json({ user: { id: 'other', email: 'other@example.test', workspaceAccess: 'allowed' } })
      : Response.json({ ok: true })
  }))
  render(<LocalizationProvider><SessionProvider><MemoryRouter><PasswordRecovery reset /></MemoryRouter></SessionProvider></LocalizationProvider>)
  await screen.findByText(/You are signed in as other@example.test/)
  fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'replacement-password' } })
  fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'replacement-password' } })
  fireEvent.click(screen.getByRole('button', { name: 'Change password' }))
  await screen.findByRole('heading', { name: 'Password changed' })
  expect(JSON.parse(String(calls.find(([path]) => path.endsWith('/reset'))![1]!.body)).userId).toBe(owner)
  expect(calls.some(([path]) => path.endsWith('/logout'))).toBe(false)
  expect(calls.some(([path]) => path.endsWith('/login'))).toBe(false)
  fireEvent.click(screen.getByRole('button', { name: 'Sign out and use another account' }))
  await waitFor(() => expect(calls.filter(([path]) => path.endsWith('/logout'))).toHaveLength(1))
})
