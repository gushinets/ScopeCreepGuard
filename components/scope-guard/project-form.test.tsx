// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

const create = vi.hoisted(() => vi.fn())
vi.mock('./store', () => ({ useStore: () => ({ createProject: create, updateProject: vi.fn(), selectedProject: null, user: { id: 'u1' }, setView: vi.fn() }) }))
vi.mock('next-intl', () => ({ useTranslations: () => (key: string) => key }))
import { NewProjectView } from './new-project-view'

beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => callback(0))
  create.mockResolvedValue({ id: 'p1' })
})
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.clearAllMocks() })

it('shows localized errors by every missing field and focuses the first one', () => {
  render(<NewProjectView />)
  fireEvent.click(screen.getByRole('button', { name: 'projects.save' }))
  expect(screen.getByText('errors.projectNameRequired')).toBeTruthy()
  expect(screen.getByText('errors.scopeRequired')).toBeTruthy()
  expect(screen.getByText('errors.startDateInvalid')).toBeTruthy()
  expect(screen.getByText('errors.hourlyRateInvalid')).toBeTruthy()
  expect(document.activeElement?.getAttribute('name')).toBe('name')
  expect(create).not.toHaveBeenCalled()
})

it('persists client name while keeping optional end date local', async () => {
  render(<NewProjectView />)
  fireEvent.change(document.querySelector('[name="name"]')!, { target: { value: 'Website' } })
  fireEvent.change(document.querySelector('[name="scope"]')!, { target: { value: 'Build the website' } })
  fireEvent.change(document.querySelector('[name="startDate"]')!, { target: { value: '2026-10-01' } })
  fireEvent.change(document.querySelector('[name="hourlyRate"]')!, { target: { value: '120' } })
  fireEvent.change(document.querySelector('[name="clientName"]')!, { target: { value: 'Acme' } })
  fireEvent.click(screen.getByRole('button', { name: 'projects.save' }))
  await waitFor(() => expect(create).toHaveBeenCalledOnce())
  expect(create.mock.lastCall?.[0]).toHaveProperty('clientName', 'Acme')
  expect(localStorage.getItem('scg:project:u1:p1')).toContain('Acme')
})
