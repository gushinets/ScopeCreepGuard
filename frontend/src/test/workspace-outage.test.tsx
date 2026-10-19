// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { routes } from '@/app/router'
import { SessionProvider } from '@/features/auth'
import en from '@/shared/i18n/messages/en.json'
import { LocalizationProvider } from '@/shared/i18n/provider'
import { workflowFixture } from './workflow-fixture'

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })
it('retains an unsaved project form when a background session refresh returns 503', async () => {
  const fixture = workflowFixture()
  document.cookie = 'locale=en; Path=/'
  const router = createMemoryRouter(routes, { initialEntries: ['/projects/new'] })
  render(<LocalizationProvider><SessionProvider><RouterProvider router={router} /></SessionProvider></LocalizationProvider>)
  const name = await screen.findByRole('textbox', { name: /Project name/ })
  fireEvent.change(name, { target: { value: 'Unconfirmed project name' } })
  fixture.state.failure = '/api/auth/me'
  fireEvent(window, new Event('focus'))
  await waitFor(() => expect(screen.getByRole('alert').textContent).toContain(en.errors.authServiceUnavailable))
  expect((screen.getByRole('textbox', { name: /Project name/ }) as HTMLInputElement).value).toBe('Unconfirmed project name')
})

it('keeps an unconfirmed project form when discard is cancelled and leaves after explicit discard', async () => {
  workflowFixture()
  document.cookie = 'locale=en; Path=/'
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
  const router = createMemoryRouter(routes, { initialEntries: ['/projects/new'] })
  render(<LocalizationProvider><SessionProvider><RouterProvider router={router} /></SessionProvider></LocalizationProvider>)
  const name = await screen.findByRole('textbox', { name: /Project name/ })
  fireEvent.change(name, { target: { value: 'Unconfirmed guarded form' } })
  fireEvent.click(screen.getByRole('button', { name: 'History' }))
  await waitFor(() => expect(confirm).toHaveBeenCalledTimes(1))
  expect((screen.getByRole('textbox', { name: /Project name/ }) as HTMLInputElement).value).toBe('Unconfirmed guarded form')
  confirm.mockReturnValue(true)
  fireEvent.click(screen.getByRole('button', { name: 'History' }))
  await screen.findByRole('heading', { name: 'History' })
})
