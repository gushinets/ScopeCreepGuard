// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { NextIntlClientProvider } from 'next-intl'
import en from '@/messages/en.json'
import ru from '@/messages/ru.json'
import type { Project } from '@/lib/types'
import { ProjectsView } from './projects-view'
import { NewProjectView } from './new-project-view'
import { ResultPanel } from './result-panel'
const state = vi.hoisted(() => ({ value: {} as Record<string, unknown>, remove: vi.fn() }))
vi.mock('./store', () => ({ useStore: () => state.value }))
const project: Project = { id: 'p1', name: 'Website', clientName: 'Acme', industry: 'Design', scope: 'Build five pages', startDate: '2026-10-01', pricingModel: 'hourly', currency: 'EUR', hourlyRate: '100.00', fixedPrice: null, history: [] }
beforeEach(() => {
  localStorage.clear()
  state.remove.mockReset().mockResolvedValue(undefined)
  state.value = { projects: [project], selectedProject: project, user: { id: 'u1' }, deleteProject: state.remove, setView: vi.fn(), selectProject: vi.fn(), status: 'idle', termsChanged: true }
})
afterEach(cleanup)
const locales = [{ locale: 'en', messages: en }, { locale: 'ru', messages: ru }] as const
it.each(locales)('uses real $locale strings in list confirmation and terms-changed feedback', async ({ locale, messages }) => {
  const view = render(<NextIntlClientProvider locale={locale} messages={messages}><ProjectsView /><ResultPanel /></NextIntlClientProvider>)
  expect(screen.getByText(messages.projects.termsChanged)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: messages.projects.deleteLabel.replace('{name}', project.name) }))
  const dialog = await screen.findByRole('alertdialog')
  expect(within(dialog).getByText(messages.projects.deleteDescription)).toBeTruthy()
  expect(dialog.textContent).toContain(project.name)
  fireEvent.click(within(dialog).getByRole('button', { name: messages.projects.cancel }))
  await waitFor(() => expect(screen.queryByRole('alertdialog')).toBeNull())
  expect(state.remove).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: messages.projects.deleteLabel.replace('{name}', project.name) }))
  fireEvent.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: messages.projects.deleteProject }))
  await waitFor(() => expect(state.remove).toHaveBeenCalledWith('p1'))
  view.unmount()
})
it.each(locales)('offers deletion from the edit form in $locale', async ({ locale, messages }) => {
  render(<NextIntlClientProvider locale={locale} messages={messages}><NewProjectView edit /></NextIntlClientProvider>)
  expect((document.querySelector('[name="clientName"]') as HTMLInputElement).value).toBe('Acme')
  fireEvent.click(screen.getByRole('button', { name: messages.projects.deleteLabel.replace('{name}', project.name) }))
  expect(await screen.findByRole('alertdialog')).toBeTruthy()
})
it('disables confirmation while pending and shows a localized error with retry', async () => {
  let fail!: (error: Error) => void
  state.remove.mockImplementationOnce(() => new Promise((_resolve, reject) => { fail = reject }))
  render(<NextIntlClientProvider locale="en" messages={en}><ProjectsView /></NextIntlClientProvider>)
  fireEvent.click(screen.getByRole('button', { name: en.projects.deleteLabel.replace('{name}', project.name) }))
  let dialog = await screen.findByRole('alertdialog')
  fireEvent.click(within(dialog).getByRole('button', { name: en.projects.deleteProject }))
  await waitFor(() => expect(within(dialog).getByRole('button', { name: en.projects.deleting }).hasAttribute('disabled')).toBe(true))
  fireEvent.click(within(dialog).getByRole('button', { name: en.projects.deleting }))
  expect(state.remove).toHaveBeenCalledTimes(1)
  fail(new Error('Network failure'))
  expect(await screen.findByRole('alert')).toHaveProperty('textContent', en.projects.deleteFailed)
  dialog = screen.getByRole('alertdialog')
  fireEvent.click(within(dialog).getByRole('button', { name: en.projects.deleteProject }))
  await waitFor(() => expect(state.remove).toHaveBeenCalledTimes(2))
})
it.each(locales)('renders the normal no-project state in $locale', ({ locale, messages }) => {
  state.value.projects = []
  state.value.selectedProject = null
  render(<NextIntlClientProvider locale={locale} messages={messages}><ProjectsView /></NextIntlClientProvider>)
  expect(screen.getByText(messages.projects.emptyTitle)).toBeTruthy()
  expect(screen.queryByRole('button', { name: messages.projects.deleteProject })).toBeNull()
})

it('passes the optional local end date separately from the project API input', async () => {
  const update = vi.fn().mockResolvedValue(project)
  state.value.updateProject = update
  render(<NextIntlClientProvider locale="en" messages={en}><NewProjectView edit /></NextIntlClientProvider>)
  fireEvent.change(document.querySelector('[name="endDate"]')!, { target: { value: '2027-01-01' } })
  fireEvent.click(screen.getByRole('button', { name: en.projects.save }))
  await waitFor(() => expect(update).toHaveBeenCalledOnce())
  expect(update.mock.calls[0][1]).not.toHaveProperty('endDate')
  expect(update.mock.calls[0][2].endDate).toBe('2027-01-01')
})
